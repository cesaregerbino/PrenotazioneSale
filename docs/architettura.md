# Architettura del Sistema — Prenotazione Sale Riunioni (MVP)

**Data:** 2026-10-18  
**Stato:** Bozza in revisione

---

## 1. Struttura delle cartelle

```
project/
├── docs/
│   ├── architettura.md          ← questo file
│   ├── requisiti.md
│   └── adr/                     ← Decisioni architetturali
│       ├── ADR-001-fastapi.md
│       ├── ADR-002-orologio-iniettato.md
│       ├── ADR-003-concorrenza.md
│       └── ADR-004-identificazione-header.md
├── app/
│   ├── __init__.py
│   ├── main.py                  ← creazione app FastAPI e configurazione
│   ├── clock.py                 ← orologio (Europe/Rome con zoneinfo), dipendenza get_now()
│   ├── database.py              ← connessione SQLite, transazioni
│   ├── models.py                ← schemi Pydantic (request/response)
│   ├── dependencies.py          ← get_current_user: estrae X-User-Email e ruolo
│   ├── api/                     ← router e endpoint
│   │   ├── __init__.py
│   │   ├── rooms.py             ← CRUD sale
│   │   ├── bookings.py          ← prenotazioni
│   │   └── availability.py      ← consultazione disponibilità
│   ├── rules/                   ← regole di business (funzioni pure)
│   │   ├── __init__.py
│   │   ├── validation.py        ← validazione orari, durata, date
│   │   └── conflict.py          ← verifica sovrapposizioni
├── tests/
│   ├── __init__.py
│   ├── conftest.py              ← fixture (DB in-memory, clock fisso)
│   ├── test_rooms.py
│   ├── test_bookings.py
│   ├── test_availability.py
│   └── test_rules/              ← test unità delle funzioni pure
│       ├── test_validation.py
│       └── test_conflict.py
├── scripts/
│   └── seed_users.py            ← popolamento tabella users
├── pyproject.toml               ← dipendenze e configurazione
└── README.md
```

**Note:**
- Nessun modulo per la gestione utenti (le operazioni CRUD sui dipendenti non sono richieste dal committente).
- I test usano un database SQLite in-memory con orologio fissato tramite fixture.
- I moduli `rules/` contengono funzioni pure che ricevono `now: datetime` come parametro — nessun accesso a stato globale.
- L'identificazione utente avviene tramite una dipendenza FastAPI (`get_current_user`), non un middleware.
- L'accesso al database usa il modulo standard `sqlite3` di Python, senza alcun ORM.

---

## 2. Schema del database

### Tabella `users`

| Colonna | Tipo | Vincoli | Note |
|---|---|---|---|
| `email` | TEXT | PRIMARY KEY | Identificatore del dipendente |
| `role` | TEXT | NOT NULL, CHECK IN ('employee', 'secretary') | Ruolo dell'utente |
| `name` | TEXT | | Opzionale, per visualizzazione |

### Tabella `rooms`

| Colonna | Tipo | Vincoli | Note |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `name` | TEXT | NOT NULL | Nome della sala |
| `floor` | TEXT | NOT NULL | Piano (es. "2°") |
| `capacity` | INTEGER | NOT NULL, CHECK > 0 | |
| `equipments` | TEXT | NOT NULL | JSON array di stringhe |
| `active` | INTEGER | NOT NULL DEFAULT 1 | 1 = attiva, 0 = disattivata |
| `created_at` | TEXT | NOT NULL | ISO datetime di creazione |

### Tabella `bookings`

| Colonna | Tipo | Vincoli | Note |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `room_id` | INTEGER | NOT NULL, FK → rooms.id | |
| `user_email` | TEXT | NOT NULL, FK → users.email | |
| `date` | TEXT | NOT NULL | Formato `YYYY-MM-DD` |
| `start_time` | TEXT | NOT NULL | Formato `HH:MM` |
| `end_time` | TEXT | NOT NULL | Formato `HH:MM` |
| `participants` | INTEGER | NOT NULL, CHECK > 0 | |
| `created_at` | TEXT | NOT NULL | ISO datetime di creazione |

**Indici:**
- `idx_bookings_room_date` ON (`room_id`, `date`) — per query di disponibilità veloci.

**Nota importante:** Non esiste alcun vincolo `UNIQUE(room_id, date, start_time)`. La prevenzione delle sovrapposizioni è gestita a livello di applicazione tramite transazione `BEGIN IMMEDIATE` (vedi sezione 6).

---

## 3. Tabella degli endpoint

### Legenda ruoli

| Simbolo | Ruolo |
|---|---|
| `EMP` | Dipendente (employee) |
| `SEC` | Segreteria (secretary) |
| `ANY` | Entrambi i ruoli |

### Endpoint

| # | Metodo | Percorso | Ruolo | User Story | Codici di risposta |
|---|---|---|---|---|---|
| 1 | `GET` | `/rooms` | `ANY` | US-01 | `200`, `401` |
| 2 | `GET` | `/rooms/all` | `SEC` | US-07, US-08 | `200`, `401`, `403` |
| 3 | `GET` | `/rooms/{room_id}/availability` | `ANY` | US-02, US-05 | `200`, `400`, `401`, `404` |
| 4 | `POST` | `/bookings` | `EMP`, `SEC` | US-03 | `201`, `400`, `401`, `404`, `409` |
| 5 | `DELETE` | `/bookings/{booking_id}` | `EMP` (solo proprie) | US-04 | `200`, `400`, `401`, `403`, `404` |
| 6 | `GET` | `/bookings/me` | `EMP` | US-05 | `200`, `401` |
| 7 | `POST` | `/rooms` | `SEC` | US-06 | `201`, `400`, `401`, `403` |
| 8 | `PUT` | `/rooms/{room_id}` | `SEC` | US-07 | `200`, `400`, `401`, `403`, `404` |
| 9 | `PATCH` | `/rooms/{room_id}/status` | `SEC` | US-08 | `200`, `400`, `401`, `403`, `404` |
| 10 | `DELETE` | `/bookings/{booking_id}` | `SEC` | US-09 | `200`, `401`, `403`, `404` |
| 11 | `GET` | `/bookings` | `SEC` | US-10 | `200`, `401`, `403` |

### Dettaglio endpoint

#### 1. `GET /rooms` — Elenco sale attive

- **User Story:** US-01
- **Descrizione:** Restituisce l'elenco delle sale attive con nome, piano, capienza ed attrezzature.
- **Risposta 200:** `{"rooms": [...]}`
- **Risposta 401:** Utente non identificato (header mancante o utente sconosciuto).

#### 2. `GET /rooms/all` — Elenco tutte le sale (incluso disattivate)

- **User Story:** US-07, US-08
- **Descrizione:** Restituisce l'elenco di **tutte** le sale, attive e disattivate, con il loro stato. Consente alla segreteria di gestire anche le sale non più in uso.
- **Risposta 200:** `{"rooms": [...]}` — Ogni sala include un campo `active` (true/false).
- **Risposta 401:** Utente non identificato.
- **Risposta 403:** Utente non è segretario.

#### 3. `GET /rooms/{room_id}/availability?date=YYYY-MM-DD` — Disponibilità sala

- **User Story:** US-02, US-05
- **Descrizione:** Restituisce le fasce orarie di 30 minuti (08:00-20:00) per la sala indicata, segnando ciascuna come `"available"` o `"occupied"`.
- **Risposta 200:** `{"room_id": 1, "date": "2026-10-20", "slots": [{"start": "08:00", "end": "08:30", "status": "available"}, ...]}`
- **Risposta 400:** Data nel passato, nel weekend, o oltre 30 giorni.
- **Risposta 404:** Sala inesistente o disattivata.
- **Risposta 401:** Utente non identificato.

#### 4. `POST /bookings` — Prenota una sala

- **User Story:** US-03
- **Descrizione:** Crea una prenotazione per una fascia oraria di 30 minuti-4 ore.
- **Body:** `{"room_id": 1, "date": "2026-10-20", "start_time": "14:00", "end_time": "14:30", "participants": 5}`
- **Risposta 201:** Prenotazione creata.
- **Risposta 400:** Orario non valido, durata eccessiva, capienza superata, partecipanti zero, fascia passata, weekend, oltre 30 giorni.
- **Risposta 401:** Utente non identificato.
- **Risposta 404:** Sala inesistente o disattivata.
- **Risposta 409:** Fascia già occupata (conflitto).

#### 5. `DELETE /bookings/{booking_id}` — Cancellazione (Dipendente)

- **User Story:** US-04
- **Descrizione:** Il dipendente cancella una propria prenotazione futura.
- **Risposta 200:** Cancellata con successo.
- **Risposta 400:** Prenotazione nel passato.
- **Risposta 403:** Tentativo di cancellare una prenotazione altrui.
- **Risposta 404:** Prenotazione inesistente.

#### 6. `GET /bookings/me` — Le proprie prenotazioni

- **User Story:** US-05
- **Descrizione:** Il dipendente visualizza le proprie prenotazioni future.
- **Risposta 200:** `{"bookings": [...]}` — Contiene sala, data, fascia oraria, numero partecipanti.
- **Risposta 401:** Utente non identificato.

#### 7. `POST /rooms` — Crea una sala (Segreteria)

- **User Story:** US-06
- **Descrizione:** L'operatore di segreteria crea una nuova sala.
- **Body:** `{"name": "Sala B", "floor": "2°", "capacity": 8, "equipments": ["projector", "lavagna"]}`
- **Risposta 201:** Sala creata, stato attivo.
- **Risposta 400:** Nome mancante, capienza ≤ 0.
- **Risposta 403:** Utente non è segretario.

#### 8. `PUT /rooms/{room_id}` — Modifica sala (Segreteria)

- **User Story:** US-07
- **Descrizione:** L'operatore modifica le informazioni di una sala esistente.
- **Risposta 200:** Sala aggiornata.
- **Risposta 403:** Utente non è segretario.
- **Risposta 404:** Sala inesistente.

#### 9. `PATCH /rooms/{room_id}/status` — Disattiva/Riattiva sala (Segreteria)

- **User Story:** US-08
- **Descrizione:** L'operatore disattiva o riattiva una sala. Alla disattivazione, le prenotazioni future vengono cancellate.
- **Body:** `{"active": false}` o `{"active": true}`
- **Risposta 200:** Stato aggiornato.
- **Risposta 403:** Utente non è segretario.
- **Risposta 404:** Sala inesistente.

#### 10. `DELETE /bookings/{booking_id}` — Cancellazione (Segreteria)

- **User Story:** US-09
- **Descrizione:** L'operatore cancella qualsiasi prenotazione, anche altrui.
- **Risposta 200:** Cancellata con successo.
- **Risposta 403:** Utente non è segretario.
- **Risposta 404:** Prenotazione inesistente.

#### 11. `GET /bookings` — Tutte le prenotazioni (Segreteria)

- **User Story:** US-10
- **Descrizione:** L'operatore visualizza tutte le prenotazioni con dettagli completi.
- **Risposta 200:** `{"bookings": [...]}` — Contiene sala, data, fascia, email del prenotatario, partecipanti.
- **Risposta 403:** Utente non è segretario.

---

### Mappa di tracciabilità endpoint ↔ user story

| User Story | Endpoint |
|---|---|
| US-01 | #1 `GET /rooms` |
| US-02 | #3 `GET /rooms/{room_id}/availability` |
| US-03 | #4 `POST /bookings` |
| US-04 | #5 `DELETE /bookings/{booking_id}` (ruolo EMP) |
| US-05 | #3 `GET /rooms/{room_id}/availability`, #6 `GET /bookings/me` |
| US-06 | #7 `POST /rooms` |
| US-07 | #2 `GET /rooms/all`, #8 `PUT /rooms/{room_id}` |
| US-08 | #2 `GET /rooms/all`, #9 `PATCH /rooms/{room_id}/status` |
| US-09 | #10 `DELETE /bookings/{booking_id}` (ruolo SEC) |
| US-10 | #11 `GET /bookings` |

**Tutte le user story sono coperte da almeno un endpoint. Tutti gli endpoint fanno riferimento ad almeno una user story.**

---

## 4. Catalogo dei codici di errore applicativi

Formato di risposta per tutti gli errori:

```json
{
    "error": {
        "code": "CODICE_ERRORE",
        "message": "Descrizione leggibile (senza dati personali)"
    }
}
```

| Codice | HTTP | Descrizione |
|---|---|---|
| `MISSING_HEADER` | `401` | Header `X-User-Email` mancante nella richiesta |
| `UNKNOWN_USER` | `401` | Email non presente nella tabella `users` |
| `INSUFFICIENT_ROLE` | `403` | Operazione riservata a un ruolo (es. segretario) |
| `INVALID_INPUT` | `400` | Dati di richiesta non validi (formato, valori) |
| `DATE_IN_PAST` | `400` | Data richiesta nel passato rispetto all'orologio di sistema |
| `DATE_WEEKEND` | `400` | Data richiesta in un giorno del weekend |
| `DATE_OUT_OF_RANGE` | `400` | Data oltre 30 giorni dal giorno corrente |
| `TIME_SLOT_INVALID` | `400` | Orario non allineato a 30 min, o fuori 08:00-20:00 |
| `DURATION_EXCEEDED` | `400` | Durata prenotazione superiore a 4 ore |
| `PARTICIPANTS_ZERO` | `400` | Numero partecipanti zero o non specificato |
| `PARTICIPANTS_EXCEED_CAPACITY` | `400` | Numero partecipanti supera la capienza della sala |
| `ROOM_NOT_FOUND` | `404` | Sala con ID indicato non esiste o è disattivata |
| `BOOKING_NOT_FOUND` | `404` | Prenotazione con ID indicato non esiste |
| `TIME_SLOT_OCCUPIED` | `409` | Fascia oraria già occupata (conflitto) |
| `SERVICE_BUSY` | `503` | Server sovraccarico (timeout modulo sqlite3) |
| `BOOKING_IN_PAST` | `400` | Tentativo di cancellare una prenotazione nel passato |
| `BOOKING_NOT_OWN` | `403` | Tentativo di cancellare una prenotazione altrui (dipendente) |

**Regola ferrea:** I messaggi di errore non contengono MAI dati personali (nome, email, o informazioni su altri utenti).

---

## 5. Orologio e gestione del tempo

### In produzione

Il modulo [`app/clock.py`](app/clock.py) espone una dipendenza FastAPI `get_now()` che restituisce `datetime.now(tz=zoneinfo.ZoneInfo("Europe/Rome"))`. `zoneinfo.ZoneInfo` gestisce automaticamente l'ora legale (DST). Il pacchetto `tzdata` è una dipendenza obbligatoria su tutte le piattaforme (aggiunta in `pyproject.toml`).

Gli endpoint chiamano `get_now()` tramite il sistema di iniezione delle dipendenze di FastAPI e passano il valore restituito alle funzioni pure di validazione nel pacchetto `app/rules/`.

### Nei test delle regole di business

Si istanzia direttamente un `datetime` fisso con `tzinfo=zoneinfo.ZoneInfo("Europe/Rome")` e lo si passa alle funzioni pure, senza alcun `mock.patch`.

### Nei test delle API

Si sostituisce la dipendenza `get_now` con un valore fisso usando `app.dependency_overrides[get_now] = lambda: datetime_fisso`. Nessun `mock.patch`.

### Vantaggi

- Le regole di business sono testabili in isolamento.
- Nessun accoppiamento con `datetime.now()` nel codice di dominio.
- Riproducibilità assoluta dei test.
- Gestione corretta dell'ora legale.
- Separazione netta tra test delle funzioni pure (datetime fisso passato come parametro) e test delle API (dependency_overrides).

---

## 6. Gestione della concorrenza

### Meccanismo

La verifica di disponibilità e l'inserimento della prenotazione avvengono nella **stessa transazione SQLite** con `BEGIN IMMEDIATE`. La sequenza è la seguente, descritta a parole:

1. Si apre una transazione con `BEGIN IMMEDIATE`, che acquisisce immediatamente un lock write sul database.
2. Si verifica che la sala esista e sia attiva.
3. Si verifica che nessuna prenotazione esistente si sovrapponga alla fascia richiesta. Due prenotazioni si sovrappongono quando l'inizio della prenotazione esistente è prima della fine della nuova prenotazione E la fine della prenotazione esistente è dopo l'inizio della nuova prenotazione. Le prenotazioni adiacenti (fine di una == inizio dell'altra) non sono sovrapposizioni e sono ammesse.
4. Si inserisce la nuova prenotazione.
5. Si esegue il `COMMIT`.

`BEGIN IMMEDIATE` apre un lock write sul database. Se un'altra richiesta è già nella transazione, SQLite acquisisce il lock e la seconda richiesta **attende** (timeout predefinito: 5 secondi del modulo `sqlite3` di Python). Quando la prima transazione termina con `COMMIT`, la seconda riprende ed esegue la verifica, che ora trova la prenotazione appena inserita e restituisce `409 TIME_SLOT_OCCUPIED`.

Se l'attesa supera il timeout di 5 secondi del modulo `sqlite3` di Python, `sqlite3` solleva `sqlite3.OperationalError: database is locked`. Questo indica un sovraccarico, non un conflitto di prenotazione, e viene restituito come `503 SERVICE_BUSY`.

L'accesso al database usa il modulo standard `sqlite3` di Python, senza alcun ORM.

### Perché funziona

Anche in un singolo processo Python, un server web ASGI (Uvicorn) esegue gli endpoint sincroni in un pool di thread gestito da FastAPI, quindi le richieste arrivano effettivamente in parallelo. Due richieste concorrenti possono quindi entrare nella sezione critica contemporaneamente. Il lock di SQLite garantisce che solo una proceda; l'altra attende e, al termine della prima, rileverà la prenotazione con una `SELECT`.

### Limiti

- Questo approccio protegge a livello di database, non a livello di applicazione. Se in futuro si introducesse caching o replicazione, servirebbero meccanismi aggiuntivi.
- Per un progetto didattico con carico basso, questo è più che sufficiente.
- SQLite è un database file-based: il lock write blocca tutte le operazioni di scrittura sul file, non solo quelle sulla stessa sala. Se il sistema cresce e ci sono molte prenotazioni concorrenti, le richieste si bloccano a vicenda.
- Il timeout di 5 secondi è il default del modulo `sqlite3` di Python. Se il sistema dovesse gestire più prenotazioni concorrenti, potrebbe essere necessario aumentarlo o ridurre il timeout per evitare attese prolungate.

---

## 7. Punti da chiarire

### Domande aperte al committente

1. **Disattivazione sala e prenotazioni passate:** La US-08 richiede che alla disattivazione di una sala le prenotazioni future vengano cancellate automaticamente. Le prenotazioni **passate** della sala disattivata vengono mantenute o rimosse?
