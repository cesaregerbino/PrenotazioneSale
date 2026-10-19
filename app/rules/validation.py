"""Regole di validazione per la prenotazione di sale (US-03).

Tutte le funzioni sono pure: ricevono `now` solo se devono confrontare
con l'orologio di sistema e non accedono a stati globali.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from zoneinfo import ZoneInfo

from app.errors import BookingRuleError

ROME = ZoneInfo("Europe/Rome")

# Limiti fissi
_BUSINESS_START = time(8, 0)
_BUSINESS_END = time(20, 0)
_DURATION_MAX = timedelta(hours=4)
_MAX_DAYS_AHEAD = 30


# ------------------------------------------------------------------
# Regole singole
# ------------------------------------------------------------------

def validate_end_after_start(start_time: time, end_time: time) -> None:
    """Verifica che l'orario di fine sia strettamente successivo all'inizio."""
    if end_time <= start_time:
        raise BookingRuleError(
            "TIME_SLOT_INVALID",
            "L'orario di fine deve essere successivo all'orario di inizio",
        )


def validate_time_alignment(start_time: time, end_time: time) -> None:
    """Verifica che inizio e fine siano allineati alla mezz'ora."""
    for t, label in [(start_time, "inizio"), (end_time, "fine")]:
        if t.minute not in (0, 30):
            raise BookingRuleError(
                "TIME_SLOT_INVALID",
                f"L'orario di {label} ({t.strftime('%H:%M')}) non è allineato a fasce di 30 minuti",
            )


def validate_duration(start_time: time, end_time: time) -> None:
    """Verifica che la durata non superi le 4 ore."""
    delta = timedelta(hours=start_time.hour, minutes=start_time.minute)
    end = timedelta(hours=end_time.hour, minutes=end_time.minute)
    duration = end - delta
    if duration > _DURATION_MAX:
        raise BookingRuleError(
            "DURATION_EXCEEDED",
            "La durata della prenotazione non può superare le 4 ore",
        )


def validate_business_hours(start_time: time, end_time: time) -> None:
    """Verifica che l'intervallo sia compreso tra 08:00 e 20:00."""
    if start_time < _BUSINESS_START:
        raise BookingRuleError(
            "TIME_SLOT_INVALID",
            "Gli orari di prenotazione iniziano alle 08:00",
        )
    if end_time > _BUSINESS_END:
        raise BookingRuleError(
            "TIME_SLOT_INVALID",
            "Gli orari di prenotazione terminano alle 20:00",
        )


def validate_weekday(start_date: date) -> None:
    """Verifica che la data non sia un giorno del weekend."""
    if start_date.weekday() >= 5:  # 5=sabato, 6=domenica
        raise BookingRuleError(
            "DATE_WEEKEND",
            "Le prenotazioni sono consentite solo dal lunedì al venerdì",
        )


def validate_not_in_past(start_date: date, start_time: time, now: datetime) -> None:
    """Verifica che la prenotazione non sia nel passato.

    La data e l'ora di inizio vengono uniti in un datetime con fuso
    Europe/Rome e confrontati con `now`. Se l'istante di inizio è
    precedente o uguale a `now`, la prenotazione è rifiutata.
    """
    start_dt = datetime(
        year=start_date.year,
        month=start_date.month,
        day=start_date.day,
        hour=start_time.hour,
        minute=start_time.minute,
        tzinfo=ROME,
    )
    if start_dt <= now:
        raise BookingRuleError(
            "DATE_IN_PAST",
            "Non è possibile prenotare fasce orarie già iniziate",
        )


def validate_within_range(start_date: date, now: datetime) -> None:
    """Verifica che la data non sia oltre 30 giorni dal giorno corrente."""
    now_date = now.astimezone(ROME).date()
    delta = start_date - now_date
    if delta.days > _MAX_DAYS_AHEAD:
        raise BookingRuleError(
            "DATE_OUT_OF_RANGE",
            "Le prenotazioni possono essere effettuate solo fino a 30 giorni avanti",
        )


def validate_participants(participants: int, capacity: int) -> None:
    """Verifica che il numero di partecipanti sia almeno 1 e non superi la capienza."""
    if participants < 1:
        raise BookingRuleError(
            "PARTICIPANTS_ZERO",
            "Il numero minimo di partecipanti è uno",
        )
    if participants > capacity:
        raise BookingRuleError(
            "PARTICIPANTS_EXCEED_CAPACITY",
            "Il numero di partecipanti supera la capienza della sala",
        )


# ------------------------------------------------------------------
# Funzione d'ingresso
# ------------------------------------------------------------------

def validate_booking(
    start_date: date,
    start_time: time,
    end_time: time,
    participants: int,
    capacity: int,
    now: datetime,
) -> None:
    """Applica tutte le regole in ordine, si ferma al primo errore.

    Ordine di applicazione:
        1. fine dopo inizio
        2. allineamento alla mezz'ora
        3. durata massima
        4. orario commerciale 08:00-20:00
        5. giorno feriale
        6. non nel passato
        7. entro 30 giorni
        8. partecipanti
    """
    validate_end_after_start(start_time, end_time)
    validate_time_alignment(start_time, end_time)
    validate_duration(start_time, end_time)
    validate_business_hours(start_time, end_time)
    validate_weekday(start_date)
    validate_not_in_past(start_date, start_time, now)
    validate_within_range(start_date, now)
    validate_participants(participants, capacity)
