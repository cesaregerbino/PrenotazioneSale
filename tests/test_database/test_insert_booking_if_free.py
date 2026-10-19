"""Test della funzione insert_booking_if_free."""

from __future__ import annotations

import datetime
import sqlite3
from datetime import date, time

import pytest

from app.db import (
    find_overlapping_bookings,
    get_connection,
    get_user,
    init_db,
    insert_booking_if_free,
    seed_db,
    transaction,
)
from app.errors import RoomNotFoundError, ServiceBusyError, TimeSlotOccupiedError


class TestInsertBookingIfFree:
    """Test completi di insert_booking_if_free."""

    @classmethod
    def setup_class(cls) -> None:
        cls.conn = get_connection(":memory:")
        init_db(cls.conn)
        cls.now = datetime.datetime(2026, 10, 19, 12, 0, 0)
        seed_db(cls.conn, cls.now)
        # Prenotazione di test: Sala A, 2026-10-20, 10:00-11:00
        cls.conn.execute(
            """INSERT INTO bookings (room_id, user_email, date, start_time, end_time, participants, created_at)
               VALUES (1, 'mario.rossi@azienda.it', '2026-10-20', '10:00', '11:00', 5, '2026-10-19T12:00:00')""",
        )

    @classmethod
    def teardown_class(cls) -> None:
        cls.conn.close()

    def _now(self) -> datetime.datetime:
        return datetime.datetime(2026, 10, 19, 12, 0, 0)

    def test_successful_booking_returns_id(self):
        """Inserimento valido restituisce ID."""
        booking_id = insert_booking_if_free(
            self.conn,
            room_id=1,
            user_email="luigi.verdi@azienda.it",
            booking_date=date(2026, 10, 25),
            start_time=time(14, 0),
            end_time=time(14, 30),
            participants=5,
            created_at=self._now(),
        )
        assert isinstance(booking_id, int)
        assert booking_id > 0

    def test_booking_persisted(self):
        """La prenotazione \u00e8 leggibile con SELECT."""
        insert_booking_if_free(
            self.conn,
            room_id=1,
            user_email="anna.bianchi@azienda.it",
            booking_date=date(2026, 10, 26),
            start_time=time(14, 0),
            end_time=time(14, 30),
            participants=3,
            created_at=self._now(),
        )
        row = self.conn.execute(
            "SELECT * FROM bookings WHERE room_id = ? AND date = ?",
            (1, "2026-10-26"),
        ).fetchall()
        assert len(row) == 1

    def test_overlapping_booking_raises(self):
        """Fascia gi\u00e0 occupata \u2192 TimeSlotOccupiedError."""
        with pytest.raises(TimeSlotOccupiedError):
            insert_booking_if_free(
                self.conn,
                room_id=1,
                user_email="luigi.verdi@azienda.it",
                booking_date=date(2026, 10, 20),
                start_time=time(10, 0),
                end_time=time(11, 0),
                participants=3,
                created_at=self._now(),
            )

    def test_inactive_room_raises(self):
        """Sala disattivata \u2192 RoomNotFoundError."""
        with pytest.raises(RoomNotFoundError):
            insert_booking_if_free(
                self.conn,
                room_id=3,
                user_email="luigi.verdi@azienda.it",
                booking_date=date(2026, 10, 27),
                start_time=time(10, 0),
                end_time=time(11, 0),
                participants=3,
                created_at=self._now(),
            )

    def test_nonexistent_room_raises(self):
        """Sala inesistente \u2192 RoomNotFoundError."""
        with pytest.raises(RoomNotFoundError):
            insert_booking_if_free(
                self.conn,
                room_id=999,
                user_email="luigi.verdi@azienda.it",
                booking_date=date(2026, 10, 28),
                start_time=time(10, 0),
                end_time=time(11, 0),
                participants=3,
                created_at=self._now(),
            )

    def test_rollback_on_error(self):
        """Errore interno: nulla rimane salvato nel DB."""
        insert_booking_if_free(
            self.conn,
            room_id=1,
            user_email="luigi.verdi@azienda.it",
            booking_date=date(2026, 10, 29),
            start_time=time(10, 0),
            end_time=time(11, 0),
            participants=3,
            created_at=self._now(),
        )
        rows = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM bookings WHERE date = '2026-10-29'"
        ).fetchone()
        assert rows["cnt"] == 1

        with pytest.raises(RoomNotFoundError):
            insert_booking_if_free(
                self.conn,
                room_id=3,
                user_email="luigi.verdi@azienda.it",
                booking_date=date(2026, 10, 29),
                start_time=time(14, 0),
                end_time=time(14, 30),
                participants=3,
                created_at=self._now(),
            )

        luigi_bookings = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM bookings WHERE date = '2026-10-29' AND user_email = 'luigi.verdi@azienda.it'"
        ).fetchone()
        assert luigi_bookings["cnt"] == 1

    def test_foreign_key_user_raises(self):
        """Prenotazione con utente inesistente \u2192 sqlite3.IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError):
            insert_booking_if_free(
                self.conn,
                room_id=1,
                user_email="non.esistente@azienda.it",
                booking_date=date(2026, 11, 1),
                start_time=time(14, 0),
                end_time=time(14, 30),
                participants=3,
                created_at=self._now(),
            )


class TestTransactionConcurrency:
    """Test di concorrenza e timeout."""

    def test_service_busy_on_lock_timeout(self, db_path: str) -> None:
        """Una connessione tiene aperta una transazione, una seconda con timeout=0.1 riceve ServiceBusyError."""
        conn1 = get_connection(db_path, timeout=30)
        init_db(conn1)
        now = datetime.datetime(2026, 10, 19, 12, 0, 0)
        seed_db(conn1, now)

        conn2 = get_connection(db_path, timeout=0.1)
        init_db(conn2)
        conn2.execute("DELETE FROM bookings")
        conn2.execute("DELETE FROM rooms")
        conn2.execute("DELETE FROM users")
        seed_db(conn2, now)

        conn1.execute("BEGIN IMMEDIATE")

        try:
            with pytest.raises(ServiceBusyError):
                with transaction(conn2):
                    get_user(conn2, "mario.rossi@azienda.it")
        finally:
            conn1.execute("ROLLBACK")
            conn1.close()
            conn2.close()


class TestTransactionRollback:
    """Test che transaction faccia ROLLBACK in caso di errore."""

    def test_rollback_on_app_error(self, db_path: str) -> None:
        """Se un'app error viene sollevato dentro transaction, il ROLLBACK avviene."""
        c = get_connection(db_path)
        now = datetime.datetime(2026, 10, 19, 12, 0, 0)
        init_db(c)
        seed_db(c, now)

        with transaction(c):
            c.execute(
                "INSERT INTO users (email, role, name) VALUES (?, ?, ?)",
                ("test@azienda.it", "employee", "Test"),
            )

        user = get_user(c, "test@azienda.it")
        assert user is not None

        try:
            with transaction(c):
                c.execute(
                    "INSERT INTO users (email, role, name) VALUES (?, ?, ?)",
                    ("rollback@azienda.it", "employee", "Rollback"),
                )
                raise RoomNotFoundError()
        except RoomNotFoundError:
            pass

        user = get_user(c, "rollback@azienda.it")
        assert user is None

        user = get_user(c, "test@azienda.it")
        assert user is not None

        c.close()


class TestTransactionPostConditions:
    """Test dello stato della connessione dopo transaction."""

    def test_begin_occupied(self, db_path: str) -> None:
        """Una connessione tiene aperta una transazione di scrittura (BEGIN IMMEDIATE);
        insert_booking_if_free con timeout 0.1 secondi solleva ServiceBusyError
        gi\u00e0 sul BEGIN IMMEDIATE; dopo, conn.in_transaction \u00e8 falso;
        chiusa la scrittura con ROLLBACK, un nuovo tentativo di prenotazione riesce."""
        now = datetime.datetime(2026, 10, 19, 12, 0, 0)

        # Seed una sola volta
        c_seed = get_connection(db_path)
        init_db(c_seed)
        seed_db(c_seed, now)
        c_seed.close()

        # conn_held: apre una transazione WRITE (BEGIN IMMEDIATE) che blocca le scritture
        conn_held = get_connection(db_path, timeout=30)
        conn_held.execute("BEGIN IMMEDIATE")
        conn_held.execute("SELECT * FROM rooms WHERE id = 1")

        # conn_write: tenta insert_booking_if_free che fa BEGIN IMMEDIATE (lock WRITE)
        # Deve attendere il lock di conn_held e poi andare in timeout
        conn_write = get_connection(db_path, timeout=0.1)
        with pytest.raises(ServiceBusyError):
            insert_booking_if_free(
                conn_write,
                room_id=1,
                user_email="luigi.verdi@azienda.it",
                booking_date=date(2026, 10, 20),
                start_time=time(14, 0),
                end_time=time(14, 30),
                participants=3,
                created_at=now,
            )

        # Dopo l'eccezione, conn_write NON deve essere in transazione
        assert conn_write.in_transaction is False

        # Chiudiamo la scrittura tenuta aperta
        conn_held.execute("ROLLBACK")
        conn_held.close()

        # Ora un nuovo tentativo deve riuscire
        conn_write2 = get_connection(db_path, timeout=5)
        booking_id = insert_booking_if_free(
            conn_write2,
            room_id=1,
            user_email="luigi.verdi@azienda.it",
            booking_date=date(2026, 10, 20),
            start_time=time(14, 0),
            end_time=time(14, 30),
            participants=3,
            created_at=now,
        )
        assert isinstance(booking_id, int)
        conn_write2.close()

    def test_commit_occupied(self, db_path: str) -> None:
        """Una connessione tiene aperta una transazione di lettura (BEGIN + SELECT);
        insert_booking_if_free sulla seconda connessione (timeout 0.1 s) deve
        sollevare ServiceBusyError; subito dopo conn.in_transaction deve essere falso;
        chiusa la lettura con COMMIT, un nuovo tentativo deve riuscire."""
        now = datetime.datetime(2026, 10, 19, 12, 0, 0)

        # Seed una sola volta
        c_seed = get_connection(db_path)
        init_db(c_seed)
        seed_db(c_seed, now)
        c_seed.close()

        # conn_read: apre una transazione di LETTURA (BEGIN senza IMMEDIATE) e tiene aperto
        conn_read = get_connection(db_path, timeout=30)
        conn_read.execute("BEGIN")
        conn_read.execute("SELECT * FROM bookings")

        # conn_write: tenta insert_booking_if_free che fa BEGIN IMMEDIATE
        # Deve attendere il lock e poi andare in timeout
        conn_write = get_connection(db_path, timeout=0.1)
        with pytest.raises(ServiceBusyError):
            insert_booking_if_free(
                conn_write,
                room_id=1,
                user_email="luigi.verdi@azienda.it",
                booking_date=date(2026, 10, 20),
                start_time=time(14, 0),
                end_time=time(14, 30),
                participants=3,
                created_at=now,
            )

        # Dopo l'eccezione, conn_write NON deve essere in transazione
        assert conn_write.in_transaction is False

        # Chiudiamo la lettura con COMMIT (non ROLLBACK, per simulare un commit normale)
        conn_read.execute("COMMIT")
        conn_read.close()

        # Ora un nuovo tentativo deve riuscire
        conn_write2 = get_connection(db_path, timeout=5)
        booking_id = insert_booking_if_free(
            conn_write2,
            room_id=1,
            user_email="luigi.verdi@azienda.it",
            booking_date=date(2026, 10, 20),
            start_time=time(14, 0),
            end_time=time(14, 30),
            participants=3,
            created_at=now,
        )
        assert isinstance(booking_id, int)
        conn_write2.close()

    def test_time_slot_occupied_after_error_not_in_transaction(self, db_path: str) -> None:
        """Dopo un TimeSlotOccupiedError la connessione non \u00e8 in transazione."""
        now = datetime.datetime(2026, 10, 19, 12, 0, 0)
        c = get_connection(db_path)
        init_db(c)
        seed_db(c, now)

        # Prima creiamo una prenotazione valida
        insert_booking_if_free(
            c,
            room_id=1,
            user_email="mario.rossi@azienda.it",
            booking_date=date(2026, 10, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            participants=5,
            created_at=now,
        )

        # Ora proviamo a sovrapporre
        with pytest.raises(TimeSlotOccupiedError):
            insert_booking_if_free(
                c,
                room_id=1,
                user_email="luigi.verdi@azienda.it",
                booking_date=date(2026, 10, 20),
                start_time=time(10, 0),
                end_time=time(11, 0),
                participants=3,
                created_at=now,
            )

        # La connessione non deve essere in transazione
        assert c.in_transaction is False
        c.close()
