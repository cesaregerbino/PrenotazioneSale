"""Test della funzione find_overlapping_bookings."""

from __future__ import annotations

import datetime
from datetime import date, time

from app.db import (
    find_overlapping_bookings,
    get_connection,
    get_room,
    init_db,
    seed_db,
)


class TestFindOverlappingBookings:
    """Test di sovrapposizione tra fasce orarie."""

    @classmethod
    def setup_class(cls) -> None:
        cls.conn = get_connection(":memory:")
        init_db(cls.conn)
        now = datetime.datetime(2026, 10, 19, 12, 0, 0)
        seed_db(cls.conn, now)
        # Prenotazione di test: Sala A, 2026-10-20, 10:00-11:00
        cls.conn.execute(
            """INSERT INTO bookings (room_id, user_email, date, start_time, end_time, participants, created_at)
               VALUES (1, 'mario.rossi@azienda.it', '2026-10-20', '10:00', '11:00', 5, '2026-10-19T12:00:00')""",
        )

    @classmethod
    def teardown_class(cls) -> None:
        cls.conn.close()

    def test_no_overlap_free_slot(self):
        """Fascia libera \u2192 lista vuota."""
        result = find_overlapping_bookings(
            self.conn, 1, date(2026, 10, 20), time(14, 0), time(14, 30)
        )
        assert result == []

    def test_exact_overlap(self):
        """Stessa fascia \u2192 1 risultato."""
        result = find_overlapping_bookings(
            self.conn, 1, date(2026, 10, 20), time(10, 0), time(11, 0)
        )
        assert len(result) == 1

    def test_partial_overlap_start(self):
        """Inizio dentro esistente \u2192 1 risultato.

        Esistente: 10:00-11:00, Nuova: 10:30-11:30
        10:00 < 11:30 AND 11:00 > 10:30 \u2192 sovrapposizione
        """
        result = find_overlapping_bookings(
            self.conn, 1, date(2026, 10, 20), time(10, 30), time(11, 30)
        )
        assert len(result) == 1

    def test_partial_overlap_end(self):
        """Fine dentro esistente \u2192 1 risultato.

        Esistente: 10:00-11:00, Nuova: 09:00-10:30
        10:00 < 10:30 AND 11:00 > 09:00 \u2192 sovrapposizione
        """
        result = find_overlapping_bookings(
            self.conn, 1, date(2026, 10, 20), time(9, 0), time(10, 30)
        )
        assert len(result) == 1

    def test_contains_existing(self):
        """Nuova fascia contiene esistente \u2192 1 risultato.

        Esistente: 10:00-11:00, Nuova: 09:00-12:00
        10:00 < 12:00 AND 11:00 > 09:00 \u2192 sovrapposizione
        """
        result = find_overlapping_bookings(
            self.conn, 1, date(2026, 10, 20), time(9, 0), time(12, 0)
        )
        assert len(result) == 1

    def test_adjacent_no_overlap_before(self):
        """Fine esistente == inizio nuovo \u2192 nessuna sovrapposizione.

        Esistente: 10:00-11:00, Nuova: 11:00-12:00
        10:00 < 12:00 (vero) AND 11:00 > 11:00 (falso) \u2192 nessuna sovrapposizione
        """
        result = find_overlapping_bookings(
            self.conn, 1, date(2026, 10, 20), time(11, 0), time(12, 0)
        )
        assert result == []

    def test_adjacent_no_overlap_after(self):
        """Fine nuovo == inizio esistente \u2192 nessuna sovrapposizione.

        Esistente: 10:00-11:00, Nuova: 09:00-10:00
        10:00 < 10:00 (falso) \u2192 nessuna sovrapposizione
        """
        result = find_overlapping_bookings(
            self.conn, 1, date(2026, 10, 20), time(9, 0), time(10, 0)
        )
        assert result == []

    def test_different_date_no_overlap(self):
        """Stessa sala, data diversa \u2192 nessuna sovrapposizione."""
        result = find_overlapping_bookings(
            self.conn, 1, date(2026, 10, 21), time(10, 0), time(11, 0)
        )
        assert result == []

    def test_different_room_no_overlap(self):
        """Stessa data/ora, sala diversa \u2192 nessuna sovrapposizione."""
        result = find_overlapping_bookings(
            self.conn, 2, date(2026, 10, 20), time(10, 0), time(11, 0)
        )
        assert result == []
