"""Eccezioni applicative condivise.

Tutte le eccezioni derivano da ``AppError`` e portano attributi
``code`` (stringa del catalogo), ``message`` (descrizione leggibile)
e ``http_status`` (codice HTTP associato).
"""

from __future__ import annotations


class AppError(Exception):
    """Eccezione applicativa base."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 500,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{code}] {message}")


# -- Regole di business ---------------------------------------------------

class BookingRuleError(AppError):
    """Violazione di una regola di business (es. orario non valido)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, http_status=400)


# -- Errori database ------------------------------------------------------

class RoomNotFoundError(AppError):
    """Sala non trovata o disattivata."""

    def __init__(self) -> None:
        super().__init__(
            "ROOM_NOT_FOUND",
            "Sala non trovata o disattivata",
            http_status=404,
        )


class TimeSlotOccupiedError(AppError):
    """Fascia oraria gi\u00e0 occupata."""

    def __init__(self) -> None:
        super().__init__(
            "TIME_SLOT_OCCUPIED",
            "Fascia oraria gi\u00e0 occupata",
            http_status=409,
        )


class ServiceBusyError(AppError):
    """Server sovraccarico (timeout SQLite)."""

    def __init__(self) -> None:
        super().__init__(
            "SERVICE_BUSY",
            "Servizio temporaneamente non disponibile",
            http_status=503,
        )
