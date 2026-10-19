"""Eccezioni per le regole di prenotazione."""

from __future__ import annotations


class BookingRuleError(Exception):
    """Eccezione sollevata quando una regola di prenotazione viene violata.

    Attributes:
        code: codice del catalogo (es. "TIME_SLOT_INVALID").
        message: messaggio in italiano.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")
