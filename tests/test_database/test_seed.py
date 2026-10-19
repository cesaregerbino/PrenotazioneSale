"""Test delle funzioni init_db e seed_db."""

from __future__ import annotations

import datetime

import pytest

from app.db import get_connection, init_db, seed_db


@pytest.fixture
def now() -> datetime.datetime:
    return datetime.datetime(2026, 10, 19, 12, 0, 0)


class TestInitDb:
    """Test che init_db crei le tabelle."""

    def test_tables_created(self, db_path: str) -> None:
        c = get_connection(db_path)
        init_db(c)
        tables = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [row["name"] for row in tables]
        assert "users" in names
        assert "rooms" in names
        assert "bookings" in names
        c.close()


class TestSeedDb:
    """Test che seed_db inserisca i dati corretti."""

    def test_four_users_created(self, conn) -> None:
        rows = conn.execute("SELECT * FROM users").fetchall()
        assert len(rows) == 4

    def test_three_rooms_created(self, conn) -> None:
        rows = conn.execute("SELECT * FROM rooms").fetchall()
        assert len(rows) == 3

    def test_user_roles(self, conn) -> None:
        rows = conn.execute("SELECT email, role FROM users").fetchall()
        roles = {r["email"]: r["role"] for r in rows}
        assert roles["mario.rossi@azienda.it"] == "employee"
        assert roles["segreteria@azienda.it"] == "secretary"

    def test_room_states(self, conn) -> None:
        rows = conn.execute("SELECT id, name, active FROM rooms").fetchall()
        active_map = {r["name"]: r["active"] for r in rows}
        assert active_map["Sala A"] == 1
        assert active_map["Sala B"] == 1
        assert active_map["Sala C"] == 0

    def test_room_capacity(self, conn) -> None:
        row = conn.execute("SELECT capacity FROM rooms WHERE name = ?", ("Sala A",)).fetchone()
        assert row["capacity"] == 10

    def test_seed_receives_now(self, db_path: str) -> None:
        """seed_db riceve now come parametro e lo usa."""
        c = get_connection(db_path)
        now = datetime.datetime(2030, 1, 1, 10, 0, 0)
        init_db(c)
        seed_db(c, now)
        row = c.execute("SELECT created_at FROM rooms LIMIT 1").fetchone()
        assert row["created_at"] == now.isoformat()
        c.close()
