# Configurazione di WhatsApp (Twilio), assistente vocale (Vapi), report ed emergenza

Nessuna chiave è scritta nel codice. Si inseriscono da **Admin › Impostazioni** (salvate nel database, tabella `secrets` per i segreti)
oppure nel file **`.env`** (vedi `.env.example`). Se un campo in admin è compilato vince quello; se è vuoto vale il `.env`.
I segreti (Auth Token Twilio, API key Vapi, secret del webhook) **non vengono mai mostrati di nuovo** né passati alle pagine pubbliche:
nel modulo compare solo "impostato". Il database `data/lmc.db` e i suoi backup contengono però le chiavi: tienili privati (`chmod 600`).

| Cosa | Campo in admin | Variabile `.env` | Dove si trova |
|---|---|---|---|
| Twilio Account SID | WhatsApp / Twilio | `TWILIO_ACCOUNT_SID` | Console Twilio, home (inizia con `AC`) |
| Twilio Auth Token | WhatsApp / Twilio | `TWILIO_AUTH_TOKEN` | Console Twilio, home › Auth Token (mostra) |
| Numero WhatsApp mittente | WhatsApp / Twilio | `TWILIO_WHATSAPP_FROM` | sandbox: `+14155238886`; produzione: il tuo mittente WhatsApp |
| Template (facoltativo) | WhatsApp / Twilio | `TWILIO_CONTENT_SID` | Messaging › Content Template Builder (`HX…`) |
| Numeri extra destinatari | WhatsApp / Twilio | `WHATSAPP_DESTINATIONS` | numeri di Pasquale/collaboratori (uno per riga o separati da virgola) |
| Vapi Public Key | Assistente vocale | `VAPI_PUBLIC_KEY` | Dashboard Vapi › API Keys › Public |
| Vapi Assistant ID | Assistente vocale | `VAPI_ASSISTANT_ID` | Dashboard Vapi › Assistants › (apri l'assistente) |
| Assistant ID emergenza | Assistente vocale | `VAPI_EMERGENCY_ASSISTANT_ID` | un secondo assistente (facoltativo) |
| Vapi API key privata | Assistente vocale | `VAPI_API_KEY` | Dashboard Vapi › API Keys › Private (serve solo al pulsante "Verifica") |
| Secret webhook | Assistente vocale | `VAPI_WEBHOOK_SECRET` | lo generi tu (pulsante "Genera secret webhook") |

> I nomi dei menu di Twilio e Vapi cambiano nel tempo: se qualcosa non coincide, cerca la voce con lo stesso nome nella loro documentazione.

## 1. WhatsApp con Twilio

### a) Prova rapida col Sandbox (gratuito, per testare)
1. Crea/accedi all'account su twilio.com › Console.
2. **Messaging › Try it out › Send a WhatsApp message**: ti mostra il numero del sandbox (di solito `+1 415 523 8886`) e un codice `join xxxx-xxxx`.
3. Da **ogni telefono che deve ricevere i messaggi** (Pasquale, collaboratori) invia su WhatsApp al numero del sandbox il testo `join xxxx-xxxx`. L'adesione scade dopo un po': se i messaggi smettono di arrivare, rimanda il codice.
4. In Admin › Impostazioni › WhatsApp / Twilio incolla **Account SID**, **Auth Token** e come mittente `+14155238886`. Salva.
5. Premi **1. Verifica credenziali**, poi **2. Invia prova** (vuoto = a chi è di turno in Team e Contatti).

### b) Produzione (numero tuo, obbligatorio per uso reale)
1. Serve un numero dedicato **non già registrato su WhatsApp** e un account **Meta Business** verificato; in Twilio: **Messaging › Senders › WhatsApp senders › Create new sender** e segui la procedura di approvazione.
2. Quando è attivo, metti quel numero in "Numero WhatsApp mittente".
3. **Regola della finestra di 24 ore (importante).** Meta consente testo libero solo entro 24 ore dall'ultimo messaggio *ricevuto* dal destinatario. I report automatici e gli avvisi spesso arrivano **fuori** da quella finestra: serve un **template approvato**.
   - In Twilio: **Messaging › Content Template Builder** › nuovo template di tipo testo, categoria *Utility*, con **una sola variabile** `{{1}}` (es. testo: `LMC Service: {{1}}`). Invialo ad approvazione.
   - Copia il **Content SID** (`HX…`) in Impostazioni › "Content SID del template". Da quel momento il sito invia tutto tramite quel template, mettendo il messaggio in `{{1}}` (a capo sostituiti da " • ", come richiesto da WhatsApp).
   - Senza template, i messaggi fuori finestra vengono rifiutati da Twilio (errore tipico `63016`) e compaiono come "errore" in Impostazioni › Ultimi invii.
4. Destinatari: **Team e Contatti** (campo "Riceve notifiche" e "Di turno") più i numeri extra. Riepiloghi chat ed emergenze vanno a chi è **di turno**; i report ai destinatari scelti per ciascun report.

### c) Cosa invia il sito su WhatsApp
- Riepilogo della chat dell'assistente (solo se il cliente lo chiede e dà il consenso) con nome, telefono, richiesta e data.
- Avviso per ogni nuovo preventivo/appuntamento (interruttore in Impostazioni).
- Richieste di richiamo dal pulsante Emergenza 24h e riepiloghi delle chiamate Vapi.
- Report giornaliero (ogni sera), settimanale (lunedì), mensile (giorno 1).
Limiti anti-abuso: massimo 3 richieste ogni 10 minuti per visitatore e tetto giornaliero (`wa_public_cap`, default 60) sugli invii nati da form pubblici.

## 2. Assistente vocale con Vapi

1. Su **dashboard.vapi.ai › Assistants** crea un assistente: lingua **italiano**, una voce italiana, primo messaggio (es. "Buongiorno, sono l'assistente di LMC Service. Come posso aiutarla?") e un prompt di sistema. Traccia consigliata:
   > Sei l'assistente vocale di LMC Service (Napoli): noleggio attrezzature audio/video/luci, ledwall, organizzazione eventi, allestimenti, videosorveglianza, in tutta Italia; aperto 24 ore. Rispondi in italiano, frasi brevi. Non inventare prezzi, disponibilità o clienti: i preventivi sono su misura. Raccogli nome, telefono, tipo di evento, data e luogo, poi conferma che Pasquale richiamerà. Per urgenze tecniche chiedi cosa è successo e il numero per il richiamo. Dichiarati assistente automatico se te lo chiedono.
2. Copia l'**Assistant ID** (pagina dell'assistente) e la **Public Key** (**API Keys › Public**). In Vapi puoi limitare la Public Key ai domini autorizzati: aggiungi il dominio del sito.
3. Incolla i valori in **Admin › Impostazioni › Assistente vocale** e salva. Sul sito, nell'assistente, compare il pulsante **✨ Voce naturale** (Vapi) accanto a "Parla con l'assistente" (voce del browser). Il componente di Vapi si scarica solo quando il cliente tocca il pulsante.
4. **Webhook per ricevere il riepilogo su WhatsApp a fine chiamata**:
   - In Admin premi **Genera secret webhook** e copia il valore (compare nel campo mascherato solo come "impostato": generalo e incollalo subito in Vapi, oppure inseriscine uno tuo nel campo e salvalo).
   - In Vapi, nell'assistente (**Advanced / Server URL**): **Server URL** = `https://IL-TUO-DOMINIO/webhook/vapi`, e come header segreto `X-Vapi-Secret` = il secret. Abilita il messaggio **end-of-call-report**.
   - Il sito risponde 404 a chi non invia il secret giusto. Il riepilogo arriva su WhatsApp a chi è di turno e compare in Admin › Chiamate e chat.
5. **Pulsante Emergenza + Vapi**: crea un secondo assistente per le urgenze e mettine l'ID in "Assistant ID per l'emergenza". Nella finestra Emergenza compare "Parla con l'assistente vocale".
6. **Chiamate telefoniche** (facoltativo): in Vapi puoi acquistare/importare un numero e associarlo all'assistente. Per far rispondere Vapi quando Pasquale non risponde, imposta sul cellulare l'**inoltro "se non risponde / occupato"** (servizio dell'operatore) verso quel numero.
7. **Verifica**: Impostazioni › "Verifica chiave e assistente" (usa la API key privata).

## 3. Report automatici
- Admin › Impostazioni › **Report automatici**: attiva/disattiva giornaliero (21:00), settimanale (lunedì 08:30), mensile (giorno 1, 08:30), cambia gli orari e scegli i destinatari tra i membri del team.
- Admin › **Report**: numeri di oggi/ieri/7/30 giorni, grafico delle visite, anteprima dei messaggi e pulsante **Invia ora**.
- Come partono: un thread del sito controlla ogni minuto; in alternativa disattivalo (`LMC_NO_BG=1`) e usa il cron: `* * * * * cd /srv/lmc && .venv/bin/python run.py --report` (e `--promemoria` ogni ora). Più processi insieme non duplicano l'invio (prenotazione atomica in `report_log`; se fallisce riprova fino a 3 volte).
- Se Twilio non è configurato i report non partono e non "bruciano" la giornata: partono appena lo configuri.
- Conteggi: visite (visitatori unici al giorno, bot esclusi, **nessun cookie e nessun IP salvato**), contatti (preventivi + riepiloghi chat + richieste emergenza + chiamate Vapi), prenotazioni, chat con l'assistente.

## 4. Emergenza 24h
Admin › Impostazioni › Emergenza 24h: attivo sì/no, numero da chiamare (vuoto = telefono di chi è di turno), orari di risposta (`24h` oppure `08:00-22:00`).
Il pulsante rosso apre una finestra con **"Chiama ora"** (`tel:`), il modulo di **richiamo urgente** (arriva subito su WhatsApp a chi è di turno) e, con Vapi, il pulsante per parlare con l'assistente. Anche l'app installata ha la scorciatoia "Emergenza".

## 5. Come testare tutto
1. Admin › Impostazioni › WhatsApp: **Verifica credenziali** → "Credenziali valide"; **Invia prova** → messaggio sul telefono.
2. Sito › Assistente: scrivi "preventivo per un matrimonio" → **Invia riepilogo su WhatsApp** → nome, telefono, consenso → arriva il messaggio.
3. Sito › **Emergenza 24h** → lascia numero e problema → arriva "🚨 EMERGENZA".
4. Admin › Report › **Invia ora** su uno dei tre report.
5. Vapi: Impostazioni › **Verifica chiave e assistente**; sul sito tocca **✨ Voce naturale** (serve HTTPS e il permesso del microfono). Per provare il webhook da terminale:
   ```
   curl -X POST https://IL-TUO-DOMINIO/webhook/vapi -H "X-Vapi-Secret: IL_SECRET" -H "Content-Type: application/json" \
     -d '{"message":{"type":"end-of-call-report","summary":"Prova: cliente chiede ledwall per matrimonio","call":{"id":"t1","customer":{"number":"+393331112222"}}}}'
   ```
6. Test automatici (senza rete, Twilio simulato): `python -m tests.test_whatsapp`.

## 6. Privacy e conformità (da far verificare a un consulente)
- Il cliente deve sapere che parla con un **assistente automatico** (avviso già nel widget) e **acconsentire** (casella non pre-spuntata) prima di inviare nome e telefono su WhatsApp.
- Aggiorna l'informativa privacy (`/privacy`, Admin › Testi) indicando i fornitori: Twilio/Meta (WhatsApp), Vapi (voce) e l'eventuale provider AI della chat, con la sede dei dati e i tempi di conservazione.
- Con la modalità vocale standard l'audio è trasformato in testo dal **browser** del cliente; con la Voce naturale passa dai server di Vapi.
- I messaggi WhatsApp di sistema a numeri che non hanno mai scritto richiedono template approvati e opt-in.

## 7. Problemi comuni (codici Twilio indicativi)
| Sintomo | Causa probabile |
|---|---|
| Ultimi invii: `63016` | Fuori dalla finestra di 24 ore: configura il template (Content SID). |
| `63015` o nessun messaggio dal sandbox | Il destinatario non ha inviato `join …` (o è scaduto). |
| `21211` | Numero destinatario non valido: controlla il prefisso internazionale. |
| `401` / "Authenticate" | Account SID o Auth Token sbagliati. |
| Il pulsante "Voce naturale" non compare | Mancano Public Key o Assistant ID. |
| Il microfono non parte | Serve HTTPS (o localhost) e il permesso del browser; Firefox non ha il riconoscimento vocale integrato. |

## Suggerimenti della chat e conversazione vocale
- **Suggerimenti**: la chat mostra 3-4 domande pronte. Di default sono generate dai dati reali del sito (primo servizio, prossima disponibilità, preventivo, emergenza o contatto del team). Per sceglierle tu: **Admin › Testi › "Suggerimenti chat"**, una domanda per riga (max 4); se il campo è vuoto tornano quelle automatiche.
- **Voce**: il microfono nella chat è sempre visibile. Con Vapi configurato (Admin › Impostazioni) usa la voce naturale Vapi; altrimenti usa la voce italiana migliore disponibile nel browser (Web Speech). Il permesso del microfono viene chiesto al primo tocco; se negato la chat spiega come riattivarlo.
