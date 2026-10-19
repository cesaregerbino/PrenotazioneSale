"""Test delle eccezioni applicative (AppError e sottoclassi) e dei reali get_now/get_db."""

from __future__ import annotations

import sqlite3

import pytest
from zoneinfo import ZoneInfo

from app.errors import (
    AppError,
    BookingRuleError,
    ServiceBusyError,
    TimeSlotOccupiedError,
    RoomNotFoundError,
)


class TestAppError:
    """Test della classe base AppError."""

    def test_has_code_message_status(self) -> None:
        err = AppError("TEST_CODE", "Test message", http_status=418)
        assert err.code == "TEST_CODE"
        assert err.message == "Test message"
        assert err.http_status == 418

    def test_string_representation(self) -> None:
        err = AppError("CODE", "Msg")
        assert "[CODE] Msg" in str(err)


class TestBookingRuleError:
    """Test che BookingRuleError sia sottoclasse di AppError."""

    def test_is_app_error(self) -> None:
        err = BookingRuleError("TIME_SLOT_INVALID", "Orario non valido")
        assert isinstance(err, AppError)
        assert err.code == "TIME_SLOT_INVALID"
        assert err.http_status == 400


class TestServiceBusyError:
    """Test ServiceBusyError."""

    def test_is_app_error(self) -> None:
        err = ServiceBusyError()
        assert isinstance(err, AppError)

    def test_code_and_status(self) -> None:
        err = ServiceBusyError()
        assert err.code == "SERVICE_BUSY"
        assert err.http_status == 503


class TestRoomNotFoundError:
    """Test RoomNotFoundError."""

    def test_is_app_error(self) -> None:
        err = RoomNotFoundError()
        assert isinstance(err, AppError)

    def test_code_and_status(self) -> None:
        err = RoomNotFoundError()
        assert err.code == "ROOM_NOT_FOUND"
        assert err.http_status == 404


class TestTimeSlotOccupiedError:
    """Test TimeSlotOccupiedError."""

    def test_is_app_error(self) -> None:
        err = TimeSlotOccupiedError()
        assert isinstance(err, AppError)

    def test_code_and_status(self) -> None:
        err = TimeSlotOccupiedError()
        assert err.code == "TIME_SLOT_OCCUPIED"
        assert err.http_status == 409


class TestGetNow:
    """Test della funzione reale get_now()."""

    def test_returns_rome_timezone(self) -> None:
        from app.clock import get_now

        now = get_now()
        assert now.tzinfo is not None
        assert str(now.tzinfo) == "Europe/Rome"

    def test_close_to_current_time(self) -> None:
        import datetime

        from app.clock import get_now

        now = get_now()
        reference = datetime.datetime.now(tz=ZoneInfo("Europe/Rome"))
        diff = abs((now - reference).total_seconds())
        assert diff < 60


class TestGetDb:
    """Test della dipendenza reale get_db()."""

    def test_foreign_keys_and_cleanup(
        self, db_path: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Override DB_PATH to use our temp database
        monkeypatch.setattr("app.dependencies.DB_PATH", db_path)

        from app.dependencies import get_db

        gen = get_db()
        conn = next(gen)

        # Verify foreign_keys are ON
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1

        # Close the generator properly (runs the finally block which closes conn)
        gen.close()

        # After close, the connection should be unusable
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
