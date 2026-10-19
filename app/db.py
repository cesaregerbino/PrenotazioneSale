"""Strato di accesso al database.

Modulo standard ``sqlite3`` senza ORM. Tutte le funzioni ricevono e
restituiscono dati semplici (dict, int, str, ``date``, ``time``).
"""

from __future__ import annotations

import contextlib
import datetime
import sqlite3
from typing import Any, Generator


from app.errors import (
    RoomNotFoundError,
    ServiceBusyError,
    TimeSlotOccupiedError,
)


# ------------------------------------------------------------------
# Helper di formattazione
# ------------------------------------------------------------------


def _fmt_time(t: datetime.time) -> str:
    """Converte un ``time`` nella stringa ``HH:MM``."""
    return t.strftime("%H:%M")


def _fmt_date(d: datetime.date) -> str:
    """Converte un ``date`` nella stringa ``YYYY-MM-DD``."""
    return d.strftime("%Y-%m-%d")


# ------------------------------------------------------------------
# Connessione
# ------------------------------------------------------------------


def get_connection(db_path: str, timeout: float = 5.0) -> sqlite3.Connection:
    """Apre e restituisce una nuova connessione SQLite.

    Imposta:
    - ``isolation_level=None`` (transazioni manuali);
    - ``row_factory = sqlite3.Row``;
    - timeout (in secondi, passato a ``sqlite3.connect``);
    - ``PRAGMA foreign_keys = ON``.
    """
    conn = sqlite3.connect(db_path, timeout=timeout, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ------------------------------------------------------------------
# Context manager di transazione
# ------------------------------------------------------------------


@contextlib.contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[None, None, None]:
    """Contesto che esegue BEGIN IMMEDIATE / COMMIT / ROLLBACK.

    Sequenza:
    1. Esegue ``BEGIN IMMEDIATE``. Se fallisce con "database is locked",
       solleva ``ServiceBusyError`` senza eseguire ROLLBACK.
    2. Esegue il blocco di lavoro e il ``COMMIT`` dentro un unico try.
    3. In caso di QUALSIASI eccezione, esegue ROLLBACK solo se
       ``conn.in_transaction`` è vero, poi:
       - se l'eccezione è ``sqlite3.OperationalError`` con "database is
         locked", solleva ``ServiceBusyError``;
       - altrimenti rilancia l'eccezione originale.
    """
    # Step 1: BEGIN IMMEDIATE
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        if "database is locked" in str(exc):
            raise ServiceBusyError() from exc
        raise

    # Step 2 + 3: lavoro + COMMIT, con ROLLBACK in caso di errore
    try:
        yield
        conn.execute("COMMIT")
    except Exception as exc:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        if isinstance(exc, sqlite3.OperationalError) and "database is locked" in str(exc):
            raise ServiceBusyError() from exc
        raise


# ------------------------------------------------------------------
# Inizializzazione schema
# ------------------------------------------------------------------

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('employee', 'secretary')),
    name TEXT
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    floor TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    equipments TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    user_email TEXT NOT NULL REFERENCES users(email),
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    participants INTEGER NOT NULL CHECK (participants > 0),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_room_date
    ON bookings (room_id, date);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Crea le tabelle del database."""
    conn.executescript(SCHEMA_SQL)


# ------------------------------------------------------------------
# Seed
# ------------------------------------------------------------------


def seed_db(conn: sqlite3.Connection, now: datetime.datetime) -> None:
    """Inserisce i dati iniziali: utenti prima, poi sale.

    Args:
        conn: connessione aperta.
        now: istante corrente da usare come ``created_at`` per sale e
             prenotazioni di seed.
    """
    now_str = now.isoformat()

    # --- Utenti ---
    conn.execute(
        "INSERT INTO users (email, role, name) VALUES (?, ?, ?)",
        ("mario.rossi@azienda.it", "employee", "Mario Rossi"),
    )
    conn.execute(
        "INSERT INTO users (email, role, name) VALUES (?, ?, ?)",
        ("luigi.verdi@azienda.it", "employee", "Luigi Verdi"),
    )
    conn.execute(
        "INSERT INTO users (email, role, name) VALUES (?, ?, ?)",
        ("anna.bianchi@azienda.it", "employee", "Anna Bianchi"),
    )
    conn.execute(
        "INSERT INTO users (email, role, name) VALUES (?, ?, ?)",
        ("segreteria@azienda.it", "secretary", "Segreteria"),
    )

    # --- Sale ---
    conn.execute(
        "INSERT INTO rooms (name, floor, capacity, equipments, active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        ("Sala A", "1\u00b0", 10, '["projector", "lavagna"]', now_str),
    )
    conn.execute(
        "INSERT INTO rooms (name, floor, capacity, equipments, active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        ("Sala B", "2\u00b0", 8, '["lavagna"]', now_str),
    )
    conn.execute(
        "INSERT INTO rooms (name, floor, capacity, equipments, active, created_at) "
        "VALUES (?, ?, ?, ?, 0, ?)",
        ("Sala C", "3\u00b0", 6, "[]", now_str),
    )


# ------------------------------------------------------------------
# Query helper
# ------------------------------------------------------------------


def get_room(conn: sqlite3.Connection, room_id: int) -> dict[str, Any] | None:
    """Restituisce la sala per ID, indipendentemente dallo stato ``active``."""
    row = conn.execute(
        "SELECT * FROM rooms WHERE id = ?", (room_id,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_user(conn: sqlite3.Connection, email: str) -> dict[str, Any] | None:
    """Restituisce l'utente per email, oppure ``None``."""
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def find_overlapping_bookings(
    conn: sqlite3.Connection,
    room_id: int,
    booking_date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
) -> list[dict[str, Any]]:
    """Trova prenotazioni sovrapposte per sala e data.

    Due prenotazioni si sovrappongono quando:
        start_esistente < end_nuova AND end_esistente > start_nuova.

    Le prenotazioni adiacenti (fine di una == inizio dell'altra)
    NON sono sovrapposizioni.
    """
    date_str = _fmt_date(booking_date)
    start_str = _fmt_time(start_time)
    end_str = _fmt_time(end_time)

    rows = conn.execute(
        """SELECT * FROM bookings
           WHERE room_id = ?
             AND date = ?
             AND start_time < ?
             AND end_time > ?""",
        (room_id, date_str, end_str, start_str),
    ).fetchall()

    return [dict(r) for r in rows]


# ------------------------------------------------------------------
# Funzione principale: inserimento prenotazione
# ------------------------------------------------------------------


def insert_booking_if_free(
    conn: sqlite3.Connection,
    *,
    room_id: int,
    user_email: str,
    booking_date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    participants: int,
    created_at: datetime.datetime,
) -> int:
    """Crea una prenotazione all'interno di una transazione ``BEGIN IMMEDIATE``.

    Sequenza (ADR-003):
    1. Verifica che la sala esista e sia attiva.
    2. Verifica che non ci siano sovrapposizioni.
    3. Inserisce la prenotazione.

    Restituisce l'ID della prenotazione creata.

    Eccezioni:
    - ``RoomNotFoundError`` se la sala non esiste o \u00e8 disattivata.
    - ``TimeSlotOccupiedError`` se la fascia \u00e8 gi\u00e0 occupata.
    - ``ServiceBusyError`` se il database \u00e8 bloccato.
    - ``sqlite3.IntegrityError`` per violazioni di chiave esterna.
    """
    with transaction(conn):
        # 1. Controlla sala
        room = get_room(conn, room_id)
        if room is None or room["active"] != 1:
            raise RoomNotFoundError()

        # 2. Controlla sovrapposizioni
        overlaps = find_overlapping_bookings(
            conn, room_id, booking_date, start_time, end_time
        )
        if overlaps:
            raise TimeSlotOccupiedError()

        # 3. Inserisce
        date_str = _fmt_date(booking_date)
        start_str = _fmt_time(start_time)
        end_str = _fmt_time(end_time)
        created_str = created_at.isoformat()

        cursor = conn.execute(
            """INSERT INTO bookings (room_id, user_email, date, start_time, end_time, participants, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (room_id, user_email, date_str, start_str, end_str, participants, created_str),
        )
        return int(cursor.lastrowid)
