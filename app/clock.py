"""Orologio di sistema con fuso Europe/Rome.

Esporta una dipendenza FastAPI `get_now()` che restituisce
l'istante corrente con fuso `Europe/Rome` tramite `zoneinfo`.
"""

from __future__ import annotations

import datetime

from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")


def get_now() -> datetime.datetime:
    """Restituisce la data/ora corrente nel fuso Europe/Rome."""
    return datetime.datetime.now(tz=ROME)
