"""Dipendenze FastAPI per l'identificazione utente e il database.

ADR-004: l'utente è identificato tramite l'header HTTP `X-User-Email`.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from fastapi import Depends, Header

from app.db import get_connection, get_user
from app.errors import AppError

# Percorso del database leggibile da variabile d'ambiente
DB_PATH = os.environ.get("PRENOTAZIONI_DB", "dev.db")


# ------------------------------------------------------------------
# get_db
# ------------------------------------------------------------------

def get_db() -> sqlite3.Connection:  # type: ignore[reportGeneralTypeIssues]
    """Apre una connessione al database e la chiude alla fine della richiesta.

    Il percorso del database si legge dalla variabile d'ambiente
    ``PRENOTAZIONI_DB``, con valore predefinito ``dev.db``.
    """
    conn = get_connection(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


# ------------------------------------------------------------------
# get_current_user
# ------------------------------------------------------------------

def get_current_user(
    email: str | None = Header(default=None, alias="X-User-Email"),
    conn: sqlite3.Connection = Depends(get_db),  # type: ignore[reportGeneralTypeIssues]
) -> dict[str, Any]:
    """Verifica l'identità dell'utente tramite header e database.

    Sequenza:
    1. Se l'header ``X-User-Email`` è mancante → 401 MISSING_HEADER.
    2. Se l'email non è trovata nel database → 401 UNKNOWN_USER.
    3. Restituisce il dict dell'utente.
    """
    if email is None or email == "":
        raise AppError("MISSING_HEADER", "Header X-User-Email mancante", 401)

    user = get_user(conn, email)
    if user is None:
        raise AppError(
            "UNKNOWN_USER",
            "Utente non riconosciuto",
            401,
        )
    return user
