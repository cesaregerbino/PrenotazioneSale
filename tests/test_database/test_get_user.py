"""Test della funzione get_user."""

from __future__ import annotations

import pytest

from app.db import get_user


class TestGetUser:
    """Test get_user."""

    def test_get_existing_employee(self, conn) -> None:
        user = get_user(conn, "mario.rossi@azienda.it")
        assert user is not None
        assert user["role"] == "employee"
        assert user["name"] == "Mario Rossi"

    def test_get_existing_secretary(self, conn) -> None:
        user = get_user(conn, "segreteria@azienda.it")
        assert user is not None
        assert user["role"] == "secretary"

    def test_get_nonexistent_user_returns_none(self, conn) -> None:
        user = get_user(conn, "non.esistente@azienda.it")
        assert user is None
