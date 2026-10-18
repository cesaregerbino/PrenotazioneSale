# ADR-004 — Identificazione utente tramite dipendenza FastAPI

- **Stato:** Proposto
- **Data:** 2026-10-18
- **Decisione:** L'utente è identificato da una dipendenza FastAPI (`get_current_user`) applicata alle route; l'identificazione avviene tramite l'header HTTP `X-User-Email`

## Contesto

Il progetto non prevede autenticazione (elemento 2 della sezione "Fuori Scope" nei requisiti). Non ci sono login, password, token JWT, o integrazione con directory aziendale. Gli utenti sono pre-caricati nel database e identificati in modo semplificato.

L'API deve comunque distinguere tra dipendente (`employee`) e operatore di segreteria (`secretary`) per applicare le autorizzazioni corrette (es. solo la segreteria può creare/modificare/disattivare sale).

## Decisione

Ogni richiesta HTTP deve includere l'header:

```
X-User-Email: mario.rossi@azienda.it
```

L'identificazione avviene tramite una **dipendenza FastAPI** (`get_current_user`) definita in `app/dependencies.py` e applicata alle route. La dipendenza estrae l'header `X-User-Email`, consulta la tabella `users` (tramite il modulo standard `sqlite3` di Python), e restituisce un oggetto utente con email e ruolo.

Questa dipendenza viene applicata alle route tramite il parametro `Depends` di FastAPI. Il ruolo (`employee` o `secretary`) viene recuperato dall'oggetto utente restituito dalla dipendenza e utilizzato nelle regole di autorizzazione.

Le regole di autorizzazione:
- Gli endpoint accessibili solo alla segreteria (`POST /rooms`, `PUT /rooms/{room_id}`, `PATCH /rooms/{room_id}/status`, `DELETE /bookings/{booking_id}` da segreteria, `GET /bookings`, `GET /rooms/all`) verificano che `user.role == 'secretary'`. Se l'utente è `employee` → `403 INSUFFICIENT_ROLE`.
- Gli endpoint accessibili a tutti verificano solo che l'utente esista (la dipendenza `get_current_user` è comunque applicata).
- La cancellazione di una prenotazione altrui da parte di un dipendente (`DELETE /bookings/{booking_id}` con `role == 'employee'`) verifica che la prenotazione appartenga all'utente corrente (`booking.user_email == user.email`). Se non corrisponde → `403 BOOKING_NOT_OWN`.

## Alternative scartate

| Alternativa | Perché scartata |
|---|---|
| **Middleware FastAPI/Starlette** | Il middleware intercetta tutte le richieste a livello di framework, ma rende il codice meno dichiarativo. Con una dipendenza, l'identificazione è esplicita nella signature della funzione e visibile nella documentazione OpenAPI. |
| **Header `X-User-Role` oltre all'email** | Raddoppia la superficie di spoofing. Meglio avere un'unica fonte di verità (la tabella `users`). |
| **Parametro di query `?user_email=...`** | Visibile negli URL, nei log del server, nella cronologia del browser. L'header è meno esposto. |
| **Cookie HTTP-only** | Richiede gestione di sessioni, CSRF protection, e configurazioni CORS complesse. Troppo pesante per un progetto didattico. |
| **Token JWT firmato** | Introduce gestione di chiavi segrete, scadenza, refresh. Il committente ha esplicitamente escluso l'autenticazione. |

## Conseguenze

### Positive

- Implementazione minimale: nessun framework di auth, nessun token, nessuna sessione.
- La tabella `users` è l'unica fonte di verità per email e ruolo.
- Semplice da testare: basta impostare l'header nella richiesta HTTP.
- Dichiarativo: la dipendenza è visibile nella signature della route e nella documentazione OpenAPI generata automaticamente.
- Allineato con la decisione del committente di usare un'identificazione semplificata (fuori scope: autenticazione).
- Niente middleware: il codice di identificazione è locale alla route, più facile da ragionare e testare.

### Negative

- **Rischio di spoofing:** chiunque può impostare `X-User-Email` con qualsiasi valore. Non c'è verifica della identità reale dell'utente. Questo è un rischio noto e accettato per l'MVP.
- **Nessun logout:** l'identità è per-request, non c'è sessione da invalidare.
- **Nessun token di sicurezza:** se in futuro si volesse aggiungere autenticazione reale, la struttura dell'header andrà sostituita (es. con `Authorization: Bearer <token>`).
