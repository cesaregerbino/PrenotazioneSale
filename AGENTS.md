# Regole per gli agenti AI

## Fonti di verità
- Requisiti: docs/requisiti.md. Architettura: docs/architettura.md. Decisioni: docs/adr/.
- Se il codice o una richiesta contraddicono questi documenti, fermati e chiedi.
- Non modificare requisiti e ADR senza una richiesta esplicita.

## Come lavorare
- Non inventare. Se un requisito non copre un caso, fermati e chiedi.
- Un compito alla volta, a piccoli passi. Non passare alla fase successiva
  senza una richiesta esplicita.
- Nessuna funzionalità senza una user story di riferimento.
- Ogni modifica al codice è accompagnata dai test relativi.
- Non dichiarare un lavoro "completato" o "verificato" senza aver eseguito
  i test e mostrato l'output.
- I calcoli su date e orari si verificano eseguendo codice, mai a mente.

## Stack
- Python 3.14, FastAPI con endpoint sincroni (def), modulo standard sqlite3
  (nessun ORM), pytest, tzdata.
- Non aggiungere dipendenze senza approvazione.
- Documenti e messaggi in italiano; codice e identificatori in inglese.
- Esegui sempre i comandi Python con l'interprete dell'ambiente virtuale:
  .venv\Scripts\python -m pip ... e .venv\Scripts\python -m pytest.


## Regole tecniche
- Le regole di business sono funzioni pure in app/rules/ e ricevono `now`
  come parametro. datetime.now() compare solo in app/clock.py.
- L'ora corrente arriva agli endpoint con la dipendenza get_now; nei test
  delle API si sostituisce con app.dependency_overrides[get_now].
- Fuso orario sempre zoneinfo.ZoneInfo("Europe/Rome").
- sqlite3: una connessione per richiesta, mai condivisa tra thread. Per usare
  BEGIN IMMEDIATE apri la connessione con isolation_level=None e gestisci
  esplicitamente BEGIN, COMMIT e ROLLBACK.
- Query SQL sempre parametrizzate (segnaposto ?), mai stringhe composte.
- Sovrapposizione: inizio esistente < fine nuova E fine esistente > inizio
  nuova. Le prenotazioni adiacenti sono ammesse.
- Errori nel formato del catalogo di docs/architettura.md; 400 e non 422
  per gli errori di validazione. Mai dati personali nei messaggi di errore.

## Sicurezza
- Mai segreti nel codice o nei file versionati.
- Non eseguire git push né comandi distruttivi (cancellazioni, git reset
  --hard, push --force) senza chiedere.
  