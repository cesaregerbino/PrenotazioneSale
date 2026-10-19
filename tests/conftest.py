"""Fixture condivise per i test.

Il database \u00e8 sempre su file temporaneo (``tmp_path`` di pytest),
mai in memoria (:memory:).
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from app.db import get_connection, init_db, seed_db


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Restituisce il percorso di un file DB temporaneo."""
    return str(tmp_path / "test.db")


@pytest.fixture
def now() -> datetime.datetime:
    """Istante fisso usato come "ora corrente" nei test."""
    return datetime.datetime(2026, 10, 19, 12, 0, 0)


@pytest.fixture
def conn(db_path: str, now: datetime.datetime):
    """Apre una connessione, inizializza lo schema e il seed, la chiude alla fine."""
    c = get_connection(db_path)
    init_db(c)
    seed_db(c, now)
    yield c
    c.close()
