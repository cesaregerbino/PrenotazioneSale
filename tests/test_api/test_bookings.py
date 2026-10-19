"""Test API per l'endpoint POST /bookings (US-03)."""

from __future__ import annotations

import datetime
import sqlite3

import pytest
from fastapi.testclient import TestClient
from zoneinfo import ZoneInfo

from app.clock import get_now
from app.dependencies import get_db
from app.main import app

ROME = ZoneInfo("Europe/Rome")
FIXED_NOW = datetime.datetime(2026, 10, 20, 10, 0, 0, tzinfo=ROME)


@pytest.fixture
def db_path(tmp_path: pytest.TempPath) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture
def conn(db_path: str):
    """Crea e popola il database di test."""
    from app.db import get_connection, init_db, seed_db

    c = get_connection(db_path)
    init_db(c)
    seed_db(c, FIXED_NOW)
    yield c
    c.close()


@pytest.fixture
def client(conn: sqlite3.Connection, db_path: str):
    """TestClient con dipendenze sovrascritte per il threading."""

    def _thread_safe_get_db():
        """Restituisce una connessione thread-safe allo stesso file DB."""
        cs = sqlite3.connect(
            db_path,
            timeout=5.0,
            isolation_level=None,
            check_same_thread=False,
        )
        cs.row_factory = sqlite3.Row
        cs.execute("PRAGMA foreign_keys = ON")
        try:
            yield cs
        finally:
            cs.close()

    app.dependency_overrides[get_now] = lambda: FIXED_NOW
    app.dependency_overrides[get_db] = _thread_safe_get_db

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()


class TestCreateBooking:
    """Test dell'endpoint POST /bookings."""

    def test_success_201(self, client: TestClient) -> None:
        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "14:00",
            "end_time": "14:30",
            "participants": 5,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["room_id"] == 1
        assert data["date"] == "2026-10-21"
        assert data["start_time"] == "14:00"
        assert data["end_time"] == "14:30"
        assert data["participants"] == 5
        assert "id" in data

    def test_missing_header_401(self, client: TestClient) -> None:
        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "14:00",
            "end_time": "14:30",
            "participants": 5,
        }
        resp = client.post("/bookings", json=body)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "MISSING_HEADER"

    def test_unknown_user_401(self, client: TestClient) -> None:
        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "14:00",
            "end_time": "14:30",
            "participants": 5,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "unknown@nonexistente.it"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNKNOWN_USER"

    def test_room_not_found_404(self, client: TestClient) -> None:
        body = {
            "room_id": 999,
            "date": "2026-10-21",
            "start_time": "14:00",
            "end_time": "14:30",
            "participants": 5,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "ROOM_NOT_FOUND"

    def test_room_inactive_404(self, client: TestClient) -> None:
        """Sala C (id=3) è disattivata."""
        body = {
            "room_id": 3,
            "date": "2026-10-21",
            "start_time": "14:00",
            "end_time": "14:30",
            "participants": 5,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "ROOM_NOT_FOUND"

    def test_time_slot_occupied_409(self, client: TestClient, conn: sqlite3.Connection) -> None:
        """Prima creo una prenotazione per la Sala A il 21/10 14:00-14:30,
        poi provo a creare una seconda prenotazione sovrapposta."""
        # Inserisci prenotazione esistente direttamente nel DB
        conn.execute(
            "INSERT INTO bookings (room_id, user_email, date, start_time, end_time, participants, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "mario.rossi@azienda.it", "2026-10-21", "14:00", "14:30", 5, FIXED_NOW.isoformat()),
        )
        conn.commit()

        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "14:00",
            "end_time": "14:30",
            "participants": 5,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "TIME_SLOT_OCCUPIED"

    def test_date_weekend_400(self, client: TestClient) -> None:
        """Sabato 24/10/2026 non è prenotabile."""
        body = {
            "room_id": 1,
            "date": "2026-10-24",
            "start_time": "14:00",
            "end_time": "14:30",
            "participants": 5,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "DATE_WEEKEND"

    def test_missing_field_400(self, client: TestClient) -> None:
        """Campo 'participants' mancante → 400 INVALID_INPUT."""
        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "14:00",
            "end_time": "14:30",
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_INPUT"

    def test_invalid_time_format_400(self, client: TestClient) -> None:
        """Valore '10.00' per start_time non è un time valido → 400 INVALID_INPUT."""
        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "10.00",
            "end_time": "14:30",
            "participants": 5,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_INPUT"
        # Il messaggio non contiene testo inglese di Pydantic
        error_msg = resp.json()["error"]["message"]
        assert "unexpected" not in error_msg.lower()
        assert "value error" not in error_msg.lower()
        assert "extra keywords" not in error_msg.lower()

    def test_zero_participants_400(self, client: TestClient) -> None:
        """0 partecipanti → 400 PARTICIPANTS_ZERO (regola di business)."""
        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "10:00",
            "end_time": "10:30",
            "participants": 0,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "PARTICIPANTS_ZERO"

    def test_no_personal_data_in_errors(self, client: TestClient) -> None:
        """Nessun messaggio di errore contiene email o nomi."""
        # Test con utente sconosciuto
        resp = client.post(
            "/bookings",
            json={
                "room_id": 1,
                "date": "2026-10-21",
                "start_time": "14:00",
                "end_time": "14:30",
                "participants": 5,
            },
            headers={"X-User-Email": "target@azienda.it"},
        )
        assert resp.status_code == 401
        error_msg = resp.json()["error"]["message"]
        assert "mario" not in error_msg.lower()
        assert "rossi" not in error_msg.lower()
        assert "target" not in error_msg.lower()
        assert "azienda" not in error_msg.lower()

    def test_partial_overlap_409(self, client: TestClient, conn: sqlite3.Connection) -> None:
        """Esistente 10:00-11:00, nuova 10:30-11:30 -> 409 TIME_SLOT_OCCUPIED."""
        conn.execute(
            "INSERT INTO bookings (room_id, user_email, date, start_time, end_time, participants, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "mario.rossi@azienda.it", "2026-10-21", "10:00", "11:00", 5, FIXED_NOW.isoformat()),
        )
        conn.commit()

        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "10:30",
            "end_time": "11:30",
            "participants": 3,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "TIME_SLOT_OCCUPIED"

    def test_adjacent_201(self, client: TestClient, conn: sqlite3.Connection) -> None:
        """Esistente 10:00-11:00, nuova 11:00-12:00 -> 201."""
        conn.execute(
            "INSERT INTO bookings (room_id, user_email, date, start_time, end_time, participants, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "mario.rossi@azienda.it", "2026-10-21", "10:00", "11:00", 5, FIXED_NOW.isoformat()),
        )
        conn.commit()

        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "11:00",
            "end_time": "12:00",
            "participants": 3,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["start_time"] == "11:00"
        assert data["end_time"] == "12:00"
        assert data["participants"] == 3

    def test_after_409_single_booking(self, client: TestClient, conn: sqlite3.Connection) -> None:
        """Dopo un 409, nel database esiste ancora una sola prenotazione."""
        conn.execute(
            "INSERT INTO bookings (room_id, user_email, date, start_time, end_time, participants, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "mario.rossi@azienda.it", "2026-10-21", "10:00", "11:00", 5, FIXED_NOW.isoformat()),
        )
        conn.commit()

        # Prima richiesta -> 409 (sovrapposizione)
        body1 = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "10:30",
            "end_time": "11:30",
            "participants": 3,
        }
        resp1 = client.post(
            "/bookings",
            json=body1,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp1.status_code == 409

        # Verifica: nel DB esiste esattamente 1 prenotazione per questa fascia
        count = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE room_id=? AND date=? AND start_time=? AND end_time=?",
            (1, "2026-10-21", "10:00", "11:00"),
        ).fetchone()[0]
        assert count == 1

    def test_after_201_booking_saved(self, client: TestClient, conn: sqlite3.Connection) -> None:
        """Dopo un 201, la prenotazione è effettivamente salvata nel database."""
        body = {
            "room_id": 1,
            "date": "2026-10-21",
            "start_time": "10:00",
            "end_time": "11:00",
            "participants": 5,
        }
        resp = client.post(
            "/bookings",
            json=body,
            headers={"X-User-Email": "mario.rossi@azienda.it"},
        )
        assert resp.status_code == 201

        # Verifica: nel DB esiste la prenotazione
        row = conn.execute(
            "SELECT room_id, date, start_time, end_time, participants FROM bookings WHERE id=?",
            (resp.json()["id"],),
        ).fetchone()
        assert row is not None
        assert row["room_id"] == 1
        assert row["date"] == "2026-10-21"
        assert row["start_time"] == "10:00"
        assert row["end_time"] == "11:00"
        assert row["participants"] == 5

    def test_openapi_schema_200(self) -> None:
        """GET /openapi.json deve restituire 200 con uno schema valido."""
        from fastapi.testclient import TestClient

        test_client = TestClient(app)
        resp = test_client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "openapi" in schema
        assert "/bookings" in schema["paths"]
