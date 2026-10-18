# Requisiti MVP — Sistema Prenotazione Sale Riunioni

## 1. User Story e Criteri di Accettazione

---

### US-01 — Visualizzazione elenco sale

> **Come** dipendente, **voglio** visualizzare l'elenco delle sale attive con nome, piano, capienza ed elenco attrezzature, **per** poter scegliere una sala adatta alle mie esigenze.

**Criteri di accettazione:**

```gherkin
Scenario: Visualizzazione elenco sale attive
  Dato che nel sistema sono presenti tre sale, di cui due attive e una disattivata
  Quando il dipendente richiede l'elenco delle sale
  Allora viene restituito l'elenco contenente solo le due sale con stato attivo
  E ogni sala include nome, piano, capienza ed elenco attrezzature

Scenario: Visualizzazione elenco vuoto
  Dato che non sono presenti sale con stato attivo
  Quando il dipendente richiede l'elenco delle sale
  Allora viene restituito un elenco vuoto
```

---

### US-02 — Visualizzazione disponibilità per fascia oraria

> **Come** dipendente, **voglio** visualizzare la disponibilità delle sale per fasce orarie di trenta minuti, **per** poter identificare gli orari liberi.

**Criteri di accettazione:**

```gherkin
Scenario: Visualizzazione disponibilità di una sala in un giorno feriale
  Dato che la sala "Sala A" è attiva
  E la sala "Sala A" ha una prenotazione dalle 10:00 alle 11:00 del martedì 20 ottobre 2026
  Quando il dipendente richiede la disponibilità della sala "Sala A" per il 20 ottobre 2026
  Allora vengono restituite fasce orarie di trenta minuti dalle 08:00 alle 20:00
  E le fasce 10:00-10:30 e 10:30-11:00 sono segnate come occupate
  E tutte le altre fasce sono segnate come disponibili

Scenario: Disponibilità non consultabile nel weekend
  Dato che la sala "Sala A" è attiva
  Quando il dipendente richiede la disponibilità della sala "Sala A" per il sabato 24 ottobre 2026
  Allora viene restituito un errore che indica che la consultazione non è consentita nel weekend

Scenario: Disponibilità non consultabile nel passato
  Dato che oggi è domenica 18 ottobre 2026
  Quando il dipendente richiede la disponibilità per il 17 ottobre 2026
  Allora viene restituito un errore che indica che non è possibile consultare date passate

Scenario: Disponibilità oltre il limite di trenta giorni
  Dato che oggi è domenica 18 ottobre 2026
  Quando il dipendente richiede la disponibilità per il 18 novembre 2026 (trentuno giorni avanti)
  Allora viene restituito un errore che indica che la consultazione è consentita solo fino a trenta giorni avanti

Scenario: Disponibilità esattamente a trenta giorni
  Dato che oggi è domenica 18 ottobre 2026
  Quando il dipendente richiede la disponibilità per il 17 novembre 2026 (esattamente trenta giorni avanti, martedì)
  Allora vengono restituite le fasce orarie disponibili per i giorni feriali
```

---

### US-03 — Prenotazione di una sala

> **Come** dipendente, **voglio** prenotare una sala per una fascia oraria di almeno trenta minuti e al massimo quattro ore, **per** poter riservare un luogo per la riunione.

**Criteri di accettazione:**

```gherkin
Scenario: Prenotazione di una fascia libera con successo
  Dato che la sala "Sala A" è attiva con capienza di dieci persone
  E la fascia 14:00-14:30 del martedì 20 ottobre 2026 è disponibile
  Quando il dipendente con email "mario.rossi@azienda.it" prenota la sala "Sala A" per la fascia 14:00-14:30 del 20 ottobre 2026 con cinque partecipanti
  Allora la prenotazione viene registrata con successo
  E la fascia 14:00-14:30 della sala "Sala A" risulta occupata

Scenario: Prenotazione con durata minima rispettata
  Dato che la sala "Sala A" è attiva
  Quando il dipendente richiede di prenotare per una fascia di trenta minuti
  Allora la prenotazione viene accettata

Scenario: Prenotazione con durata massima esatta rispettata
  Dato che la sala "Sala A" è attiva
  Quando il dipendente richiede di prenotare per quattro ore esatte (otto fasce consecutive)
  Allora la prenotazione viene accettata

Scenario: Prenotazione che supera la durata massima
  Dato che la sala "Sala A" è attiva
  Quando il dipendente richiede di prenotare per quattro ore e trenta minuti (nove fasce consecutive)
  Allora la prenotazione viene rifiutata con un errore che indica la durata massima di quattro ore

Scenario: Prenotazione che supera la capienza della sala
  Dato che la sala "Sala A" è attiva con capienza di dieci persone
  Quando il dipendente con email "mario.rossi@azienda.it" prenota la sala "Sala A" con dodici partecipanti
  Allora la prenotazione viene rifiutata con un errore che indica che il numero di partecipanti supera la capienza

Scenario: Prenotazione con numero partecipanti zero
  Dato che la sala "Sala A" è attiva
  Quando il dipendente tenta di prenotare con zero partecipanti
  Allora la prenotazione viene rifiutata con un errore che indica che il numero minimo di partecipanti è uno

Scenario: Prenotazione di una fascia già occupata (conflitto)
  Dato che la sala "Sala A" ha già una prenotazione per la fascia 10:00-10:30 del martedì 20 ottobre 2026
  Quando il dipendente con email "luigi.verdi@azienda.it" richiede di prenotare la stessa sala per la stessa fascia
  Allora la prenotazione viene rifiutata con un errore che indica che la fascia è già occupata
  E la prima prenotazione registrata viene mantenuta

Scenario: Prenotazione con sovrapposizione parziale
  Dato che la sala "Sala A" ha una prenotazione per la fascia 10:00-11:00 del martedì 20 ottobre 2026
  Quando il dipendente richiede di prenotare la fascia 10:30-11:00
  Allora la prenotazione viene rifiutata con un errore che indica la sovrapposizione

Scenario: Prenotazione di fascia adiacente consentita
  Dato che la sala "Sala A" ha una prenotazione per la fascia 10:00-11:00 del martedì 20 ottobre 2026
  Quando il dipendente richiede di prenotare la fascia 11:00-12:00
  Allora la prenotazione viene accettata con successo

Scenario: Prenotazione nel futuro troppo lontano
  Dato che oggi è domenica 18 ottobre 2026
  Quando il dipendente richiede di prenotare per il 18 novembre 2026 (trentuno giorni avanti)
  Allora la prenotazione viene rifiutata con un errore che indica il limite di trenta giorni

Scenario: Prenotazione esattamente a trenta giorni
  Dato che oggi è domenica 18 ottobre 2026
  E la fascia 14:00-14:30 del 17 novembre 2026 (trenta giorni avanti, martedì) è disponibile
  Quando il dipendente richiede di prenotare per il 17 novembre 2026
  Allora la prenotazione viene accettata

Scenario: Prenotazione nel passato
  Quando il dipendente richiede di prenotare per una data passata
  Allora la prenotazione viene rifiutata con un errore che indica che non è possibile prenotare nel passato

Scenario: Prenotazione nel weekend
  Quando il dipendente richiede di prenotare per il sabato 24 ottobre 2026
  Allora la prenotazione viene rifiutata con un errore che indica che le prenotazioni sono consentite solo dal lunedì al venerdì

Scenario: Prenotazione fascia iniziale accettata
  Dato che oggi è lunedì 19 ottobre 2026
  E la fascia 08:00-08:30 del 19 ottobre 2026 è disponibile
  Quando il dipendente richiede di prenotare la fascia 08:00-08:30
  Allora la prenotazione viene accettata con successo

Scenario: Prenotazione fascia finale accettata
  Dato che oggi è lunedì 19 ottobre 2026
  E la fascia 19:30-20:00 del 19 ottobre 2026 è disponibile
  Quando il dipendente richiede di prenotare la fascia 19:30-20:00
  Allora la prenotazione viene accettata con successo

Scenario: Prenotazione che inizia prima delle 08:00
  Dato che oggi è lunedì 19 ottobre 2026
  Quando il dipendente richiede di prenotare la fascia 07:30-08:30
  Allora la prenotazione viene rifiutata con un errore che indica che gli orari iniziano alle 08:00

Scenario: Prenotazione che finisce dopo le 20:00
  Dato che oggi è lunedì 19 ottobre 2026
  Quando il dipendente richiede di prenotare la fascia 19:30-20:30
  Allora la prenotazione viene rifiutata con un errore che indica che gli orari terminano alle 20:00

Scenario: Prenotazione con orario non allineato alla mezzora
  Dato che oggi è lunedì 19 ottobre 2026
  Quando il dipendente richiede di prenotare la fascia 10:15-10:45
  Allora la prenotazione viene rifiutata con un errore che indica che gli orari devono essere allineati a fasce di trenta minuti

Scenario: Prenotazione fine precedente all'inizio
  Dato che oggi è lunedì 19 ottobre 2026
  Quando il dipendente richiede di prenotare la fascia 11:00-10:00 (fine precedente all'inizio)
  Allora la prenotazione viene rifiutata con un errore che indica che l'orario di fine deve essere successivo all'orario di inizio

Scenario: Prenotazione di fascia già passata oggi
  Dato che oggi è lunedì 19 ottobre 2026 e sono le 11:00
  Quando il dipendente richiede di prenotare la fascia 09:00-09:30 di oggi
  Allora la prenotazione viene rifiutata con un errore che indica che la fascia è già passata
```

---

### US-04 — Cancellazione prenotazione da parte del dipendente

> **Come** dipendente, **voglio** cancellare le mie prenotazioni future, **per** poter liberare una sala se non mi serve più.

**Criteri di accettazione:**

```gherkin
Scenario: Cancellazione di una prenotazione futura con successo
  Dato che il dipendente con email "mario.rossi@azienda.it" ha una prenotazione attiva per la sala "Sala A" il martedì 20 ottobre 2026
  Quando "mario.rossi@azienda.it" richiede la cancellazione della propria prenotazione
  Allora la prenotazione viene cancellata con successo
  E la fascia oraria diventa nuovamente disponibile

Scenario: Cancellazione di una prenotazione non propria non permessa
  Dato che il dipendente con email "mario.rossi@azienda.it" ha una prenotazione attiva per la sala "Sala A"
  Quando il dipendente con email "luigi.verdi@azienda.it" tenta di cancellare la prenotazione di "mario.rossi@azienda.it"
  Allora la cancellazione viene rifiutata con un errore che indica che è possibile cancellare solo le proprie prenotazioni

Scenario: Cancellazione di una prenotazione nel passato non permessa
  Dato che il dipendente con email "mario.rossi@azienda.it" ha una prenotazione registrata nel passato
  Quando "mario.rossi@azienda.it" tenta di cancellarla
  Allora la cancellazione viene rifiutata con un errore che indica che non è possibile cancellare prenotazioni passate

Scenario: Cancellazione di una prenotazione tra trenta giorni
  Dato che il dipendente con email "mario.rossi@azienda.it" ha una prenotazione tra trenta giorni
  Quando "mario.rossi@azienda.it" richiede la cancellazione
  Allora la cancellazione viene accettata
```

---

### US-05 — Visualizzazione stato occupazione senza identità del prenotatario

> **Come** dipendente, **voglio** vedere se una sala è occupata in una certa fascia oraria senza conoscere l'identità di chi ha prenotato, **per** rispettare la privacy dei colleghi.

**Criteri di accettazione:**

```gherkin
Scenario: Visualizzazione stato occupazione senza dati personali
  Dato che la sala "Sala A" ha una prenotazione per la fascia 10:00-11:00 del martedì 20 ottobre 2026 effettuata da "mario.rossi@azienda.it"
  Quando il dipendente con email "luigi.verdi@azienda.it" consulta la disponibilità della sala "Sala A" per il 20 ottobre 2026
  Allora la fascia 10:00-11:00 viene mostrata come occupata
  E l'indirizzo email "mario.rossi@azienda.it" non viene visualizzato

Scenario: Visualizzazione proprie prenotazioni future
  Dato che il dipendente con email "mario.rossi@azienda.it" ha una prenotazione attiva per la sala "Sala A"
  Quando "mario.rossi@azienda.it" consulta le proprie prenotazioni
  Allora visualizza i dettagli della propria prenotazione: sala, data, fascia oraria, numero partecipanti
```

---

### US-06 — Creazione di una nuova sala (Segreteria)

> **Come** operatore di segreteria, **voglio** creare una nuova sala con nome, piano, capienza ed elenco attrezzature, **per** aggiungere sale disponibili al sistema.

**Criteri di accettazione:**

```gherkin
Scenario: Creazione di una sala con successo
  Dato che l'operatore di segreteria accede all'endpoint di creazione sala
  Quando l'operatore invia i dati: nome "Sala B", piano "2°", capienza 8, attrezzature ["projector", "lavagna"]
  Allora la sala viene creata con stato attivo
  E la sala è immediatamente visibile nell'elenco delle sale

Scenario: Creazione di una sala senza nome
  Quando l'operatore tenta di creare una sala senza specificare il nome
  Allora la creazione viene rifiutata con un errore che indica che il nome è obbligatorio

Scenario: Creazione di una sala con capienza zero
  Quando l'operatore tenta di creare una sala con capienza pari a zero
  Allora la creazione viene rifiutata con un errore che indica che la capienza deve essere maggiore di zero

Scenario: Creazione di una sala con capienza negativa
  Quando l'operatore tenta di creare una sala con capienza negativa
  Allora la creazione viene rifiutata con un errore che indica che la capienza deve essere maggiore di zero
```

---

### US-07 — Modifica di una sala esistente (Segreteria)

> **Come** operatore di segreteria, **voglio** modificare le informazioni di una sala esistente (nome, piano, capienza, attrezzature), **per** tenere aggiornati i dati delle sale.

**Criteri di accettazione:**

```gherkin
Scenario: Modifica dei dati di una sala attiva con successo
  Dato che la sala "Sala A" esiste con capienza di dieci persone
  Quando l'operatore di segreteria modifica la capienza a dodici
  Allora la sala viene aggiornata con la nuova capienza

Scenario: Modifica di una sala disattivata
  Dato che la sala "Sala C" è disattivata
  Quando l'operatore di segreteria modifica i dati della sala
  Allora la modifica viene accettata
  E la sala rimane disattivata dopo la modifica

Scenario: Tentativo di modifica di una sala inesistente
  Quando l'operatore di segreteria tenta di modificare una sala con identificativo non esistente
  Allora viene restituito un errore che indica che la sala non esiste
```

---

### US-08 — Disattivazione e riattivazione di una sala (Segreteria)

> **Come** operatore di segreteria, **voglio** disattivare o riattivare una sala, **per** gestirne la disponibilità (es. manutenzione).

**Criteri di accettazione:**

```gherkin
Scenario: Disattivazione di una sala attiva
  Dato che la sala "Sala A" è attiva
  Quando l'operatore di segreteria disattiva la sala
  Allora la sala passa a stato disattivata
  E non appare più nell'elenco delle sale visibili ai dipendenti
  E non è più possibile effettuare prenotazioni per quella sala
  E le prenotazioni future della sala "Sala A" vengono cancellate

Scenario: Disattivazione di una sala già disattivata
  Dato che la sala "Sala A" è già disattivata
  Quando l'operatore tenta di disattivarla nuovamente
  Allora la sala rimane disattivata
  E non viene restituito alcun errore

Scenario: Riattivazione di una sala disattivata
  Dato che la sala "Sala A" è disattivata
  Quando l'operatore di segreteria riattiva la sala
  Allora la sala passa a stato attivo
  E torna visibile nell'elenco delle sale
```

---

### US-09 — Cancellazione prenotazione da parte della Segreteria

> **Come** operatore di segreteria, **voglio** cancellare qualsiasi prenotazione anche quelle di altri utenti, **per** gestire emergenze o necessità operative.

**Criteri di accettazione:**

```gherkin
Scenario: Cancellazione di una prenotazione altrui con successo
  Dato che il dipendente con email "mario.rossi@azienda.it" ha una prenotazione per la sala "Sala A"
  Quando l'operatore di segreteria cancella tale prenotazione
  Allora la prenotazione viene rimossa
  E la fascia oraria diventa nuovamente disponibile

Scenario: Cancellazione di una prenotazione inesistente
  Dato che non esiste una prenotazione con l'identificativo fornito
  Quando l'operatore di segreteria tenta di cancellarla
  Allora viene restituito un errore che indica che la prenotazione non esiste
```

---

### US-10 — Visualizzazione tutte le prenotazioni (Segreteria)

> **Come** operatore di segreteria, **voglio** visualizzare tutte le prenotazioni con i dettagli completi inclusi l'identificativo del dipendente, **per** avere una visione completa dell'utilizzo delle sale.

**Criteri di accettazione:**

```gherkin
Scenario: Visualizzazione elenco tutte le prenotazioni
  Dato che esistono prenotazioni attive per più sale
  Quando l'operatore di segreteria richiede l'elenco di tutte le prenotazioni
  Allora viene restituito l'elenco completo con: sala, data, fascia oraria, email del dipendente prenotatario, numero partecipanti

Scenario: Visualizzazione prenotazioni per sala
  Dato che la sala "Sala A" ha tre prenotazioni attive
  Quando l'operatore richiede le prenotazioni della sala "Sala A"
  Allora viene restituito l'elenco delle tre prenotazioni con tutti i dettagli
```

---

## 2. Fuori Scope

Di seguito tutte le funzionalità esplicitamente escluse dall'MVP:

| # | Funzionalità | Motivazione |
|---|-------------|-------------|
| 1 | Interfaccia grafica (frontend web o mobile) | L'MVP è solo un'API REST |
| 2 | Autenticazione e autorizzazione (login, password, token, integrazione directory aziendale) | Gli utenti sono pre-caricati e identificati in modo semplificato |
| 3 | Modifica di una prenotazione (cambio orario o sala) | L'utente deve cancellare e riprenotare |
| 4 | Notifiche email o promemoria | Non richiesto dal committente |
| 5 | Check-in e check-out della sala | Non richiesto dal committente |
| 6 | Prenotazioni ricorrenti (es. ogni lunedì) | Non richiesto dal committente |
| 7 | Gestione risorse correlate (projector, catering, ecc.) come entità separate | Le attrezzature sono un semplice elenco nella sala |
| 8 | Sale suddivisibili in zone | Tutte le sale sono intere |
| 9 | Orari di disponibilità differenziati per sala | Tutti gli orari sono 08:00-20:00 dal lunedì al venerdì |
| 10 | Report e statistiche di utilizzo | Non richiesto dal committente |
| 11 | Approvazione o priorità di prenotazione | Nessuna approvazione, nessuna priorità |
| 12 | Applicazione mobile (iOS o Android) | Fuori scope |
| 13 | Integrazione con Outlook, Google Calendar, Teams o Slack | Fuori scope |
| 14 | Gestione delle code d'attesa per sale occupate | Fuori scope |
| 15 | Cancellazione automatica per inattività (no-show) | Fuori scope |

---

## 3. Risposte del Committente

Di seguito le risposte fornite dal committente alle domande iniziali, che integrano i requisiti:

| ID | Area | Risposta del committente |
|----|------|--------------------------|
| R1 | Identificazione utente | Il dipendente è identificato dall'email aziendale |
| R2 | Numero partecipanti | Il numero di partecipanti è obbligatorio, valore minimo 1 |
| R3 | Disattivazione sala | Disattivando una sala, le sue prenotazioni future vengono cancellate automaticamente |
| R4 | Storico prenotazioni dipendente | Il dipendente vede solo le proprie prenotazioni future |
| R5 | Riattivazione sala | La riattivazione di una sala disattivata è consentita |
| R6 | Consultazione disponibilità | La disponibilità è consultabile solo da oggi a trenta giorni avanti, nei giorni feriali; altrimenti errore chiaro |
| R7 | Disattivazione già disattivata | Disattivare una sala già disattivata non restituisce errore, la sala rimane disattivata |

---

## 4. Decisioni Tecniche Rimandate alla Progettazione

Di seguito le informazioni di natura tecnica che non sono state definite dal committente e che saranno oggetto della fase di progettazione:

| ID | Area | Domanda |
|----|------|---------|
| T1 | Utenti | Dove e come vengono pre-caricati i dati dei dipendenti? Chi inserisce i nuovi dipendenti? Esiste un file CSV di import? |
| T2 | Prenotazione | Qual è il formato della fascia oraria in prenotazione? Il sistema accetta un orario di inizio con durata oppure un intervallo di partenza e arrivo? |
| T3 | Autorizzazione | Come viene distinto un operatore di segreteria da un dipendente normale a livello di API? Esiste un campo "ruolo" sull'utente o un header HTTP dedicato? |
| T4 | API | Qual è il formato di risposta per gli errori? Codici HTTP standard con body JSON strutturato con campo di errore? |
| T5 | API | Le date e gli orari usano quale formato e fuso orario? |
| T6 | Database | Qual è lo schema delle tabelle? Tabelle `users`, `rooms`, `bookings` con quali campi esatti? |
| T7 | Disponibilità | L'endpoint di disponibilità restituisce tutte le sale per una data giornata, o va specificata una sala per volta? |
| T8 | Disponibilità | Cosa viene restituito per le fasce orarie in cui la sala non è prenotabile (es. prima delle 08:00 o dopo le 20:00)? Vengono omesse o segnate come non prenotabili? |
| T9 | Sala | Le attrezzature sono un semplice elenco di stringhe o hanno struttura più complessa con tipo e valore? |
| T10 | Conflitti | Qual è il codice HTTP di risposta in caso di conflitto (prenotazione doppia)? |
| T11 | Storico | Serve un endpoint per la paginazione dell'elenco delle prenotazioni o delle sale? |
