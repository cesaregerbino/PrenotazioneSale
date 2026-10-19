"""Test delle regole di validazione prenotazione (US-03).

Ogni test viola una sola regola quando è un test negativo.
I test positivi verificano che nessuna regola venga violata.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.errors import BookingRuleError
from app.rules.validation import (
    validate_business_hours,
    validate_booking,
    validate_duration,
    validate_end_after_start,
    validate_not_in_past,
    validate_participants,
    validate_time_alignment,
    validate_weekday,
    validate_within_range,
)

ROME = ZoneInfo("Europe/Rome")

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _now(date_str: str) -> datetime:
    """Costruisce un `now` timezone-aware a mezzogiorno."""
    return datetime.fromisoformat(date_str).replace(tzinfo=ROME)


# ------------------------------------------------------------------
# validate_end_after_start
# ------------------------------------------------------------------

class TestValidateEndAfterStart:
    """Regola: end_time deve essere strettamente successivo a start_time."""

    def test_valid(self) -> None:
        validate_end_after_start(time(14, 0), time(14, 30))  # non solleva

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_end_after_start(time(11, 0), time(10, 0))
        assert exc.value.code == "TIME_SLOT_INVALID"

    def test_end_equal_start_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_end_after_start(time(10, 0), time(10, 0))
        assert exc.value.code == "TIME_SLOT_INVALID"


# ------------------------------------------------------------------
# validate_time_alignment
# ------------------------------------------------------------------

class TestValidateTimeAlignment:
    """Regola: inizio e fine devono essere allineati alla mezz'ora."""

    def test_valid(self) -> None:
        validate_time_alignment(time(14, 0), time(14, 30))  # non solleva

    def test_invalid_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_time_alignment(time(10, 15), time(10, 45))
        assert exc.value.code == "TIME_SLOT_INVALID"


# ------------------------------------------------------------------
# validate_duration
# ------------------------------------------------------------------

class TestValidateDuration:
    """Regola: durata massima 4 ore (superamento)."""

    def test_min_valid(self) -> None:
        validate_duration(time(14, 0), time(14, 30))  # non solleva

    def test_max_valid(self) -> None:
        validate_duration(time(14, 0), time(18, 0))  # non solleva

    def test_too_long_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_duration(time(14, 0), time(18, 30))
        assert exc.value.code == "DURATION_EXCEEDED"


# ------------------------------------------------------------------
# validate_business_hours
# ------------------------------------------------------------------

class TestValidateBusinessHours:
    """Regola: orario compreso tra 08:00 e 20:00."""

    def test_valid_start(self) -> None:
        validate_business_hours(time(8, 0), time(8, 30))  # non solleva

    def test_valid_end(self) -> None:
        validate_business_hours(time(19, 30), time(20, 0))  # non solleva

    def test_start_too_early_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_business_hours(time(7, 30), time(8, 30))
        assert exc.value.code == "TIME_SLOT_INVALID"

    def test_end_too_late_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_business_hours(time(19, 30), time(20, 30))
        assert exc.value.code == "TIME_SLOT_INVALID"


# ------------------------------------------------------------------
# validate_weekday
# ------------------------------------------------------------------

class TestValidateWeekday:
    """Regola: solo giorni feriali (lunedì-venerdì)."""

    def test_valid_tuesday(self) -> None:
        validate_weekday(date(2026, 10, 20))  # martedì, non solleva

    def test_saturday_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_weekday(date(2026, 10, 24))  # sabato
        assert exc.value.code == "DATE_WEEKEND"

    def test_sunday_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_weekday(date(2026, 10, 25))  # domenica
        assert exc.value.code == "DATE_WEEKEND"


# ------------------------------------------------------------------
# validate_not_in_past
# ------------------------------------------------------------------

class TestValidateNotInPast:
    """Regola: la prenotazione deve essere nel futuro (inizio > now)."""

    def test_future_date_ok(self) -> None:
        now = _now("2026-10-18T12:00:00")
        validate_not_in_past(date(2026, 10, 20), time(14, 0), now)  # non solleva

    def test_past_date_raises(self) -> None:
        now = _now("2026-10-18T12:00:00")
        with pytest.raises(BookingRuleError) as exc:
            validate_not_in_past(date(2026, 10, 17), time(14, 0), now)
        assert exc.value.code == "DATE_IN_PAST"

    def test_today_past_slot_raises(self) -> None:
        now = _now("2026-10-19T11:00:00")
        with pytest.raises(BookingRuleError) as exc:
            validate_not_in_past(date(2026, 10, 19), time(9, 0), now)
        assert exc.value.code == "DATE_IN_PAST"

    def test_today_exact_start_raises(self) -> None:
        """Una prenotazione che inizia esattamente all'istante now è rifiutata."""
        now = _now("2026-10-19T11:00:00")
        with pytest.raises(BookingRuleError) as exc:
            validate_not_in_past(date(2026, 10, 19), time(11, 0), now)
        assert exc.value.code == "DATE_IN_PAST"

    def test_today_future_slot_ok(self) -> None:
        now = _now("2026-10-19T11:00:00")
        validate_not_in_past(date(2026, 10, 19), time(14, 0), now)  # non solleva


# ------------------------------------------------------------------
# validate_within_range
# ------------------------------------------------------------------

class TestValidateWithinRange:
    """Regola: al massimo 30 giorni avanti."""

    def test_30_days_ok(self) -> None:
        now = _now("2026-10-18T12:00:00")
        validate_within_range(date(2026, 11, 17), now)  # 30 giorni, non solleva

    def test_31_days_raises(self) -> None:
        now = _now("2026-10-18T12:00:00")
        with pytest.raises(BookingRuleError) as exc:
            validate_within_range(date(2026, 11, 18), now)  # 31 giorni
        assert exc.value.code == "DATE_OUT_OF_RANGE"


# ------------------------------------------------------------------
# validate_participants
# ------------------------------------------------------------------

class TestValidateParticipants:
    """Regola: almeno 1 partecipante, non oltre la capienza."""

    def test_valid(self) -> None:
        validate_participants(5, 10)  # non solleva

    def test_zero_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_participants(0, 10)
        assert exc.value.code == "PARTICIPANTS_ZERO"

    def test_exceed_raises(self) -> None:
        with pytest.raises(BookingRuleError) as exc:
            validate_participants(12, 10)
        assert exc.value.code == "PARTICIPANTS_EXCEED_CAPACITY"


# ------------------------------------------------------------------
# validate_booking (funzione d'ingresso)
# ------------------------------------------------------------------

class TestValidateBooking:
    """Test della funzione d'ingresso validate_booking()."""

    def _now(self, s: str) -> datetime:
        return datetime.fromisoformat(s).replace(tzinfo=ROME)

    def test_all_valid_no_error(self) -> None:
        """Prenotazione completamente valida: nessun errore."""
        now = self._now("2026-10-19T10:00:00")
        validate_booking(
            start_date=date(2026, 10, 20),
            start_time=time(14, 0),
            end_time=time(14, 30),
            participants=5,
            capacity=10,
            now=now,
        )  # non solleva

    def test_order_duration_over_weekend(self) -> None:
        """sabato 24/10, 14:00-18:30: errore DURATION_EXCEEDED (regola 3, prima di weekday)."""
        now = self._now("2026-10-19T10:00:00")
        with pytest.raises(BookingRuleError) as exc:
            validate_booking(
                start_date=date(2026, 10, 24),
                start_time=time(14, 0),
                end_time=time(18, 30),
                participants=5,
                capacity=10,
                now=now,
            )
        assert exc.value.code == "DURATION_EXCEEDED"

