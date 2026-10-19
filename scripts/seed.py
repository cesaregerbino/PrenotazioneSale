"""Seed script for creating and populating the database."""

from __future__ import annotations

import os
import sys

from app.clock import get_now
from app.db import get_connection, init_db, seed_db

DB_PATH = os.environ.get("PRENOTAZIONI_DB", "dev.db")


def main() -> None:
    if os.path.exists(DB_PATH):
        print(f"Il database '{DB_PATH}' esiste già. Nessun intervento effettuato.")
        sys.exit(0)

    now = get_now()
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        seed_db(conn, now)
    finally:
        conn.close()

    print(f"Database '{DB_PATH}' creato e popolato con successo.")


if __name__ == "__main__":
    main()
