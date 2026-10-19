"""Test della funzione get_room."""

from __future__ import annotations

import pytest

from app.db import get_room


class TestGetRoom:
    """Test get_room."""

    def test_get_active_room(self, conn) -> None:
        room = get_room(conn, 1)
        assert room is not None
        assert room["name"] == "Sala A"
        assert room["active"] == 1

    def test_get_inactive_room_returns_room(self, conn) -> None:
        """get_room restituisce la sala anche se disattivata."""
        room = get_room(conn, 3)
        assert room is not None
        assert room["name"] == "Sala C"
        assert room["active"] == 0

    def test_get_nonexistent_room_returns_none(self, conn) -> None:
        room = get_room(conn, 999)
        assert room is None

    def test_get_second_active_room(self, conn) -> None:
        room = get_room(conn, 2)
        assert room is not None
        assert room["name"] == "Sala B"
        assert room["capacity"] == 8
