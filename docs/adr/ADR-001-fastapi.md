# ADR-001 — Framework web: FastAPI

- **Stato:** Proposto
- **Data:** 2026-10-18
- **Decisione:** FastAPI con endpoint sincroni (def, non async def)

## Contesto

Il progetto richiede un framework Python per esporre un'API REST con SQLite. I vincoli sono: semplicità didattica, minimo di dipendenze, nessun processo aggiuntivo, nessuna infrastruttura esterna.

## Decisione

Si utilizza **FastAPI** con endpoint definiti tramite `def` (sincroni). FastAPI supporta nativamente sia endpoint sincroni che asincroni; scegliendo `def` si evita di introdurre l'asincronia nel codice di dominio.

Il server di produzione gira su **Uvicorn** in modalità single-worker. Gli endpoint sincroni di FastAPI vengono eseguiti in un pool di thread gestito da FastAPI, quindi le richieste sono effettivamente concorrenti.

## Alternative scartate

| Alternativa | Perché scartata |
|---|---|
| **Flask** | Framework più semplice, ma richiede configurazione manuale di validazione, serializzazione e documentazione OpenAPI. FastAPI offre tutto questo "out of the box" con Pydantic. |
| **Django REST Framework** | Troppo pesante per un progetto didattico con SQLite e nessuna esigenza di ORM complesso, admin panel, o sessione-based auth. |
| **FastAPI con endpoint `async def`** | L'asincronia richiede che TUTTO lo stack (database, logica) sia asincrono. SQLite non ha driver asincrono nativo senza estensioni. Semplicemente non vale la complessità introdotta. |

## Conseguenze

### Positive

- Validazione automatica dei dati di richiesta tramite schemi Pydantic.
- Documentazione OpenAPI automatica (Swagger UI a `/docs`).
- Endpoint sincroni: codice leggibile, debuggabile, insegnabile.
- Zero configurazione per la serializzazione/deserializzazione JSON.
- Gli endpoint sincroni di FastAPI vengono eseguiti in un pool di thread, quindi le richieste sono effettivamente concorrenti.

### Negative

- Gli utenti Flask potrebbero trovare FastAPI meno immediato all'inizio, ma la curva di apprendimento è moderata.
- Il codice di dominio non può usare `await` — tutto deve essere sincrono, il che è una limitazione voluta per semplicità.
