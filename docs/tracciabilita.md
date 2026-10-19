# Matrice di Tracciabilità — User Story US-03

> **User Story:** Prenotazione di una sala
> **Stack:** Python 3.14, FastAPI, sqlite3, pytest, zoneinfo

## Livelli di verifica

| Livello | Codice | Test | Ruolo |
|---------|--------|------|-------|
| Regole | [`../app/rules/validation.py`](../app/rules/validation.py) | [`../tests/test_rules/test_validation.py`](../tests/test_rules/test_validation.py) | Funzioni pure, `now` come parametro |
| Database | [`../app/db.py`](../app/db.py) | [`../tests/test_database/`](../tests/test_database/) | Query parametrizzate, transazioni |
| API | [`../app/main.py`](../app/main.py) | [`../tests/test_api/test_bookings.py`](../tests/test_api/test_bookings.py) | Dependency injection, override `get_now` |

## Tabella di tracciabilità

Legenda: **R** = Regole, **D** = Database, **A** = API.
Tutti gli scenari sono verificati nel loro esito completo, cioè in tutti i passi «Allora». La colonna Livelli indica a quali livelli avviene la verifica.

| # | Scenario US-03 | Regole | Database | API | Livelli |
|---|----------------|--------|----------|-----|---------|
| 1 | Prenotazione fascia libera con successo | `TestValidateBooking/test_all_valid_no_error` | `TestFindOverlappingBookings/test_no_overlap_free_slot`, `TestInsertBookingIfFree/test_successful_booking_returns_id`, `TestInsertBookingIfFree/test_booking_persisted` | `TestCreateBooking/test_success_201`, `TestCreateBooking/test_after_201_booking_saved` | R + D + A |
| 2 | Durata minima (30 min) rispettata | `TestValidateDuration/test_min_valid` | — | — | R |
| 3 | Durata massima (4 ore) esatta rispettata | `TestValidateDuration/test_max_valid` | — | — | R |
| 4 | Durata supera massimo (4h30) | `TestValidateDuration/test_too_long_raises` | — | — | R |
| 5 | Supera capienza sala | `TestValidateParticipants/test_exceed_raises` | — | — | R |
| 6 | Numero partecipanti zero | `TestValidateParticipants/test_zero_raises` | — | `TestCreateBooking/test_zero_participants_400` | R + A |
| 7 | Fascia già occupata (conflitto) | — | `TestFindOverlappingBookings/test_exact_overlap`, `TestInsertBookingIfFree/test_overlapping_booking_raises` | `TestCreateBooking/test_time_slot_occupied_409`, `TestCreateBooking/test_after_409_single_booking` | D + A |
| 8 | Sovrapposizione parziale | — | `TestFindOverlappingBookings/test_partial_overlap_start`, `TestFindOverlappingBookings/test_partial_overlap_end` | `TestCreateBooking/test_partial_overlap_409` | D + A |
| 9 | Fascia adiacente consentita | — | `TestFindOverlappingBookings/test_adjacent_no_overlap_before`, `TestFindOverlappingBookings/test_adjacent_no_overlap_after` | `TestCreateBooking/test_adjacent_201` | D + A |
| 10 | Futuro troppo lontano (>30 gg) | `TestValidateWithinRange/test_31_days_raises` | — | — | R |
| 11 | Esattamente 30 giorni | `TestValidateWithinRange/test_30_days_ok` | — | — | R |
| 12 | Prenotazione nel passato | `TestValidateNotInPast/test_past_date_raises` | — | — | R |
| 13 | Prenotazione nel weekend | `TestValidateWeekday/test_saturday_raises`, `TestValidateWeekday/test_sunday_raises` | — | `TestCreateBooking/test_date_weekend_400` | R + A |
| 14 | Fascia iniziale accettata (08:00) | `TestValidateBusinessHours/test_valid_start` | — | — | R |
| 15 | Fascia finale accettata (19:30-20:00) | `TestValidateBusinessHours/test_valid_end` | — | — | R |
| 16 | Inizio prima delle 08:00 | `TestValidateBusinessHours/test_start_too_early_raises` | — | — | R |
| 17 | Fine dopo le 20:00 | `TestValidateBusinessHours/test_end_too_late_raises` | — | — | R |
| 18 | Orario non allineato alla mezzora | `TestValidateTimeAlignment/test_invalid_raises` | — | — | R |
| 19 | Fine precedente all'inizio | `TestValidateEndAfterStart/test_end_before_start_raises` | — | — | R |
| 20 | Fascia già passata oggi | `TestValidateNotInPast/test_today_past_slot_raises` | — | — | R |
| 21 | Inizio esattamente all'istante corrente | `TestValidateNotInPast/test_today_exact_start_raises` | — | — | R |
| 22 | Orario con secondi ≠ 0 | `TestValidateTimeAlignment/test_with_seconds_raises` | — | — | R |
| 23 | Fine uguale all'inizio | `TestValidateEndAfterStart/test_end_equal_start_raises` | — | — | R |

## Riepilogo per codice di errore

| Codice errore | Scenario | Test regole | Test DB | Test API |
|---------------|----------|-------------|---------|----------|
| `DATE_IN_PAST` | Passato / istante corrente / fascia passata | `TestValidateNotInPast/test_past_date_raises`, `test_today_exact_start_raises`, `test_today_past_slot_raises` | — | — |
| `DATE_WEEKEND` | Weekend | `TestValidateWeekday/test_saturday_raises`, `test_sunday_raises` | — | `TestCreateBooking/test_date_weekend_400` |
| `DATE_OUT_OF_RANGE` | > 30 giorni | `TestValidateWithinRange/test_31_days_raises` | — | — |
| `DURATION_EXCEEDED` | > 4 ore | `TestValidateDuration/test_too_long_raises` | — | — |
| `PARTICIPANTS_ZERO` | 0 partecipanti | `TestValidateParticipants/test_zero_raises` | — | `TestCreateBooking/test_zero_participants_400` |
| `PARTICIPANTS_EXCEED_CAPACITY` | > capienza | `TestValidateParticipants/test_exceed_raises` | — | — |
| `TIME_SLOT_INVALID` | Non allineato / secondi / fine ≤ inizio / fuori orari | `TestValidateEndAfterStart/test_end_before_start_raises`, `test_end_equal_start_raises`; `TestValidateTimeAlignment/test_invalid_raises`, `test_with_seconds_raises`; `TestValidateBusinessHours/test_start_too_early_raises`, `test_end_too_late_raises` | — | — |
| `TIME_SLOT_OCCUPIED` | Conflitto / sovrapposizione | — | `TestFindOverlappingBookings/test_exact_overlap`, `test_partial_overlap_start`, `test_partial_overlap_end`; `TestInsertBookingIfFree/test_overlapping_booking_raises` | `TestCreateBooking/test_time_slot_occupied_409`, `test_partial_overlap_409` |

## Verifica di integrità API aggiuntiva

| Test | Cosa verifica |
|------|---------------|
| `TestCreateBooking/test_missing_header_401` | Assenza header `X-User-Email` → 401 |
| `TestCreateBooking/test_unknown_user_401` | Email non in DB → 401 |
| `TestCreateBooking/test_room_not_found_404` | `room_id` inesistente → 404 |
| `TestCreateBooking/test_room_inactive_404` | Sala disattivata → 404 |
| `TestCreateBooking/test_missing_field_400` | Campo `participants` mancante → 400 |
| `TestCreateBooking/test_invalid_time_format_400` | Valore `"10.00"` per `start_time` → 400 INVALID_INPUT |
| `TestCreateBooking/test_no_personal_data_in_errors` | Nessun dato personale nei messaggi |
| `TestCreateBooking/test_after_409_single_booking` | Rollback su conflitto |
| `TestCreateBooking/test_after_201_booking_saved` | Persistenza su successo |
| `TestCreateBooking/test_openapi_schema_200` | Schema OpenAPI valido |

## Scelte di copertura

### Piramide dei test

Le regole di business ([`../app/rules/validation.py`](../app/rules/validation.py)) sono funzioni pure e vengono
verificate in modo **esaustivo a livello unitario**: ogni combinazione valida e
non valida di ogni singolo validatore ha il proprio test in
[`../tests/test_rules/test_validation.py`](../tests/test_rules/test_validation.py).

La verifica API ([`../tests/test_api/test_bookings.py`](../tests/test_api/test_bookings.py)) segue il principio della
**piramide dei test**: per ciascun percorso diverso (successo, vari codici di
errore, integrità transazionale) esiste un **singolo test** che attraversa
l'intero stack (regole → database → API). Questo garantisce che l'integrazione
tra i livelli funzioni senza duplicare la copertura logica.

### Ramo non coperto in `transaction()`

Il rilancio dell'errore in `transaction()` quando `BEGIN IMMEDIATE` fallisce
per un motivo diverso da "database is locked" (il `raise` sulla riga dell'`else`
di `isinstance(exc, sqlite3.OperationalError)`) è lasciato intenzionalmente
scoperto perché:

1. Rappresenta un percorso di errore di basso livello (fallimento del database
   non legato a una regola di business).
2. Non è possibile simularlo in test in ambiente controllato senza introdurre
   dipendenze esterne o modifiche intrusive al codice.
