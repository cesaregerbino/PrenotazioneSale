"""Test delle eccezioni applicative (AppError e sottoclassi)."""

from __future__ import annotations

import pytest

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
