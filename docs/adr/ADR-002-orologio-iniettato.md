# ADR-002 — Orologio iniettato come dipendenza FastAPI

- **Stato:** Proposto
- **Data:** 2026-10-18
- **Decisione:** La data/ora corrente è fornita agli endpoint tramite una dipendenza FastAPI (`get_now` in `app/clock.py`); gli endpoint passano il valore alle funzioni pure di validazione

## Contesto

Molti scenari di test fissano "oggi" a una data precisa (es. martedì 20 ottobre 2026). Le regole di validazione — "non prenotare nel passato", "non prenotare nel weekend", "massimo 30 giorni avanti" — dipendono tutte dalla data/ora corrente. Se il codice di dominio chiama `datetime.now()` direttamente, i test diventano non deterministici o richiedono `mock.patch`, che accoppia i test all'implementazione.

## Decisione

Tutte le funzioni di validazione e regola ricevono `now: datetime` come parametro esplicito. Le regole di business sono funzioni pure: non leggono lo stato del sistema, non accedono al database, non chiamano `datetime.now()`.

In produzione, il modulo `app/clock.py` espone una dipendenza FastAPI `get_now()` che restituisce `datetime.now(tz=zoneinfo.ZoneInfo("Europe/Rome"))`. `zoneinfo.ZoneInfo` gestisce automaticamente l'ora legale (DST). Il pacchetto `tzdata` è una dipendenza obbligatoria su tutte le piattaforme (aggiunta in `pyproject.toml`). Gli endpoint chiamano `get_now()` tramite la dipendenza FastAPI e passano il valore restituito a tutte le funzioni di regola.

Nei test delle regole di business, si istanzia direttamente un `datetime` fisso con `tzinfo=zoneinfo.ZoneInfo("Europe/Rome")` e lo si passa alle funzioni pure, senza alcun mocking.

Nei test delle API, si sostituisce la dipendenza `get_now` con un valore fisso usando `app.dependency_overrides[get_now] = lambda: datetime(2026, 10, 20, 10, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Rome"))`. Nessun `mock.patch`.

## Alternative scartate

| Alternativa | Perché scartata |
|---|---|
| **`datetime.now()` diretto nel codice di dominio** | Rende le funzioni non testabili in isolamento; i test devono patchare il modulo, creando fragilità. |
| **`unittest.mock.patch` su `datetime`** | Aggiunge complessità ai test e accoppia i test all'implementazione. Se si cambia la funzione che legge l'orologio, tutti i test patchati si rompono. |
| **Singleton globale `Clock`** | Introduce stato globale nascosto, più difficile da testare e da ragionare. |
| **Offset fisso (es. UTC+1)** | Non gestisce l'ora legale. `zoneinfo.ZoneInfo` è necessario per un corretto cambio tra CET (UTC+1) e CEST (UTC+2). |

## Conseguenze

### Positive

- Funzioni di dominio 100% testabili in isolamento con qualsiasi valore di `now`.
- Nessuna dipendenza da stato globale o da mocking.
- La logica di business è esposta chiaramente: la data corrente è un input, non un effetto collaterale.
- Semplice da insegnare: separazione netta tra effetto collaterale (leggere l'orologio) e logica pura.
- Gestione corretta dell'ora legale con `zoneinfo`.
- Test API con `dependency_overrides`: meccanismo nativo di FastAPI, chiaro e manutenibile.

### Negative

- Ogni funzione che ha bisogno della data corrente deve riceverla come parametro. Questo può sembrare verboso, ma rende le dipendenze esplicite.
- La catena di chiamata deve passare `now` da un livello all'altro. Con la struttura modulare proposta (regole pure nel pacchetto `app/rules/`), il livello endpoint è l'unico che chiama `get_now()` e passa il valore alle funzioni di regola.
- Il pacchetto `tzdata` è una dipendenza aggiuntiva obbligatoria su tutte le piattaforme.
