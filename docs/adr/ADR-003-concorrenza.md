# ADR-003 — Gestione concorrenza: transazione BEGIN IMMEDIATE

- **Stato:** Proposto
- **Data:** 2026-10-18
- **Decisione:** Verifica di disponibilità e inserimento della prenotazione avvengono nella stessa transazione SQLite con `BEGIN IMMEDIATE`; i timeout restituiscono `503 SERVICE_BUSY`

## Contesto

Due prenotazioni per la stessa sala, stessa data, stessa fascia oraria non devono essere entrambe accettate: vince la prima registrata. Anche se il sistema gira in un singolo processo Python, un server web ASGI (Uvicorn) esegue gli endpoint sincroni in un pool di thread gestito da FastAPI, quindi le richieste arrivano effettivamente in parallelo. Due richieste concorrenti possono quindi entrare nella sezione critica contemporaneamente.

Un approccio "leggi-verifica-inserisci" in tre step separati senza lock è soggetto a race condition: due thread possono leggere la stessa disponibilità, entrambi verificare che la fascia è libera, e entrambi inserire — creando un duplicato.

## Decisione

Si usa una transazione SQLite con `BEGIN IMMEDIATE`. La sequenza è la seguente, descritta a parole senza codice:

1. Si apre una transazione con `BEGIN IMMEDIATE`, che acquisisce immediatamente un lock write sul database.
2. Si verifica che la sala esista e sia attiva.
3. Si verifica che nessuna prenotazione esistente si sovrapponga alla fascia richiesta. Due prenotazioni si sovrappongono quando l'inizio della prenotazione esistente è prima della fine della nuova prenotazione E la fine della prenotazione esistente è dopo l'inizio della nuova prenotazione. Le prenotazioni adiacenti (fine di una == inizio dell'altra) non sono sovrapposizioni e sono ammesse.
4. Si inserisce la nuova prenotazione.
5. Si esegue il `COMMIT`.

`BEGIN IMMEDIATE` apre un lock write sul database SQLite. Se un'altra richiesta è già nella transazione, SQLite acquisisce il lock e la seconda richiesta attende (timeout predefinito: 5 secondi del modulo `sqlite3` di Python). Quando la prima transazione termina con `COMMIT`, la seconda riprende ed esegue la verifica, che ora trova la prenotazione appena inserita e restituisce `409 TIME_SLOT_OCCUPIED`.

Perché `BEGIN IMMEDIATE` e non `BEGIN DEFERRED`? Con `DEFERRED`, il lock viene acquisito solo al primo comando di scrittura, ma due thread potrebbero entrambi leggere (lock shared) e poi entrambi tentare di scrivere (lock upgrade fallisce). Con `BEGIN IMMEDIATE`, il lock write è acquisito immediatamente, bloccando gli altri thread.

Se l'attesa supera il timeout di 5 secondi del modulo `sqlite3` di Python, `sqlite3` solleva `sqlite3.OperationalError: database is locked`. Questo indica un sovraccarico, non un conflitto di prenotazione, e viene restituito come `503 SERVICE_BUSY`.

L'accesso al database usa il modulo standard `sqlite3` di Python, senza alcun ORM.

## Alternative scartate

| Alternativa | Perché scartata |
|---|---|
| **Lock ottimistico (senza lock DB)** | Due thread leggono la stessa disponibilità, entrambi inseriscono. Serve un vincolo UNIQUE o un controllo post-inserimento con rollback, che darebbe una falsa sicurezza (vedi architettura: senza UNIQUE, le sovrapposizioni parziali non sono coperte). |
| **Lock a livello di applicazione (threading.Lock)** | Funziona solo in un singolo processo Python. Se in futuro si deployasse con più worker, il lock non proteggerebbe più. Meglio delegare al DB. |
| **Lock file system o Redis** | Introduce infrastruttura esterna. Violerebbe il vincolo "nessuna infrastruttura aggiuntiva". |
| **Lock row-level su tabella bookings** | SQLite non supporta lock per riga; solo lock a livello di database. `BEGIN IMMEDIATE` è la soluzione più vicina. |

## Conseguenze

### Positive

- La race condition è gestita a livello di database, non di applicazione.
- Il lock write assicura che una sola transazione per volta possa verificare e inserire per la stessa fascia.
- Nessuna infrastruttura esterna: SQLite è la scelta già fatta dal committente.
- Se due richieste concorrenti arrivano, una viene accettata e l'altra rileva la prenotazione con una `SELECT` post-lock.
- I timeout sono gestiti chiaramente: `503 SERVICE_BUSY` indica sovraccarico, non un errore di business logic.
- Nessun ORM: si usa il modulo standard `sqlite3` di Python, che non richiede dipendenze aggiuntive.

### Negative

- SQLite è un database file-based: il lock write blocca tutte le operazioni di scrittura sul file, non solo quelle sulla stessa sala. Se il sistema cresce e ci sono molte prenotazioni concorrenti, le richieste si bloccano a vicenda. Per un progetto didattico con carico basso è accettabile.
- Il timeout di 5 secondi è il default del modulo `sqlite3` di Python. Se il sistema dovesse gestire più prenotazioni concorrenti, potrebbe essere necessario aumentarlo o ridurre il timeout per evitare attese prolungate.
