# Guida completa al pannello Admin – LMC Service

Indirizzo: `https://TUO-DOMINIO/admin` (in locale `http://localhost:5000/admin`). Il menu a sinistra è diviso in sezioni, qui nello stesso ordine.
Etichette in alto: **DEMO** = dati finti e bollini «Demo» sul sito, **PRODUCTION** = sito reale (si cambia con `APP_MODE` nel file `.env`).

> **Primo accesso:** vai subito in **Altro › 🔐 Cambia password** (almeno 10 caratteri). Il login si blocca 5 minuti dopo 5 tentativi sbagliati.

---

## 1. SITO

### ✏️ Testi (`/admin/testi`) – tutto il contenuto del sito in un solo modulo
| Gruppo | Campi | Dove compare |
|---|---|---|
| **Identità** | Nome attività, Nome breve, Titolare, Città, Data di fondazione | Titoli, footer, «Chi siamo», PDF, assistente |
| **Hero e storia** | Claim (frase principale: la seconda frase dopo il punto va su una seconda riga in oro), Sottotitolo, Chi siamo (storia) | Hero, «Chi siamo» |
| **Contatti** | Zone coperte, Telefono, WhatsApp (solo numeri con prefisso: `393661782548`), Email, Indirizzo/città, Orari | Contatti, pulsanti Chiama/WhatsApp, banda CTA, FAQ, assistente |
| **Social** | Instagram (URL), Facebook (URL), Facebook – nome pagina, TikTok (URL), Sito ufficiale (URL) | Sezione Contatti e footer «Seguici» (una voce senza URL sparisce da sola) |
| **Legale** | Dati societari nel footer (ragione sociale, P.IVA, sede legale), Informativa privacy (testo principale), Informativa privacy (dettagli: fornitori, sede dei dati, conservazione, basi giuridiche) | Footer, pagina `/privacy`, intestazione dei PDF |
| **Assistente** | Suggerimenti chat (una domanda per riga, max 4; vuoto = automatici dai dati del sito) | Chip nella chat «Assistente LMC AI» |
| **Servizi** | Fino a 6 servizi (nome + descrizione) | Sezione «Le nostre skill», assistente |
| **Cifre in evidenza** | Una per riga: `Etichetta \| numero \| suffisso` (es. `Eventi realizzati \| 150 \| +`) | Sezione «In cifre». Solo dati veri: vuoto = nessuna cifra inventata |
| **Frasi dell'intro** | Una per riga | Didascalie dell'intro cinematografica |

Salva con **Salva tutto**. Un campo che non è nel modulo non viene mai azzerato.

### 🖼️ Foto e video (`/admin/foto`)
- **Carica**: più file insieme (foto fino a 12 MB, video fino a 60 MB). Le foto vengono ottimizzate in automatico (versioni 400/800/1600 px WebP).
- Per ogni elemento: titolo, didascalia, categoria (Eventi, Installazioni, Show Demo, Audio, Luci, Video, Progettazione, Meeting), caselle **Mostra in home / in galleria / nell'intro**, **In evidenza** (una sola: è la prima foto della hero), **Nascondi**, **Elimina**.
- **Riordina** trascinando.
- **Sincronizza cartella `foto/organizzate`**: pubblica le foto/video nuove copiate nelle sottocartelle `hero`, `galleria`, `installazioni`, `video` (succede anche a ogni avvio del sito). Quelle spostate o cancellate dalla cartella spariscono dal sito. Il **primo video** (per ordine) è quello «In evidenza» nella sezione Show demo (oggi il reel America's Cup); accanto a `video-01.mp4` si può mettere `video-01.poster.jpg` come locandina, altrimenti si usa un fotogramma.
- **Migliorare le foto prima di caricarle** (esposizione, colore, rumore, nitidezza leggeri, orientamento): `python -m backend.enhance_foto` — gli originali restano in `foto/_originali/`.
- Il segnaposto «FOTO IN ARRIVO» compare finché non ci sono foto reali.

### 🧑‍🤝‍🧑 Team e Contatti (`/admin/m/team`)
Nome, ruolo, telefono/WhatsApp, email, nota (orari), **Mostra sul sito e all'assistente** (sì/no), ordine, **Riceve notifiche e report su WhatsApp**, **Di turno** (riceve i riepiloghi chat e le emergenze). Chi è «di turno» è il destinatario delle emergenze: tieni almeno una persona di turno.

### ⭐ Dicono di noi (`/admin/m/recensioni`)
Autore, testo, fonte. **Solo recensioni vere**. In produzione la sezione appare solo se c'è almeno una recensione.

---

## 2. PRENOTAZIONI

### 📅 Calendario (dashboard `/admin/`)
Agenda dei prossimi appuntamenti con **Conferma / Annulla** (il cliente riceve l'email), contatori di preventivi nuovi e appuntamenti in attesa, prossimi eventi.

### 📨 Richieste (`/admin/richieste`)
- **Appuntamenti**: stato in attesa / confermato / annullato / completato (alla conferma o annullamento il cliente riceve un'email).
- **Preventivi**: stato nuova / in lavorazione / inviata / chiusa e **+ Cliente** per trasformare la richiesta in una scheda cliente.
- Il cliente può spostare/annullare da solo dal link ricevuto per email.

### 🕒 Disponibilità (`/admin/disponibilita`)
- **Fasce settimanali** (giorno, dalle–alle), con **Aggiungi fascia** / **Elimina**.
- **Giorni di chiusura** (ferie, festivi) con data e nota: **Chiudi giorno / Riapri**.
- **Durata di ogni appuntamento** in minuti.
- Di default: lun–ven 10–13 e 16–19. **Cambiala con gli orari reali.**

### 📞 Chiamate e chat (`/admin/chiamate`)
Registro di chiamate dell'assistente vocale (Vapi), riepiloghi chat e richieste di emergenza.

---

## 3. REPORT

### 📊 Report e visite (`/admin/report`)
- Visite degli ultimi 14 giorni (anonime e aggregate), richieste, chat, chiamate.
- **Invia ora** un report su WhatsApp (giornaliero, settimanale, mensile) e storico degli **ultimi invii**.

---

## 4. IMPOSTAZIONI (`/admin/impostazioni`)
Le chiavi si salvano nel database (**ciò che inserisci qui ha la precedenza sul file `.env`**) e i campi segreti non vengono mai mostrati di nuovo: si può solo sostituirli o cancellarli.

| Scheda | Cosa contiene | Servizio esterno |
|---|---|---|
| 💬 **WhatsApp / Twilio** | Account SID, Auth Token (segreto), numero mittente, Content SID del template (facoltativo, serve per scrivere oltre le 24 h), altri destinatari, interruttore «avvisa a ogni richiesta». Pulsanti **1. Verifica credenziali** e **2. Messaggio di prova** | Twilio |
| 🎙️ **Assistente vocale** | Public Key, Assistant ID, Assistant ID per l'emergenza, API Key privata (solo per il test), Secret del webhook (con pulsante **Genera**). Pulsante **Verifica assistente** | Vapi |
| ⏰ **Report automatici** | Per giornaliero/settimanale/mensile: attivo sì/no, orario, destinatari (scelti tra il Team) | Twilio |
| 🚨 **Emergenza 24h** | Pulsante rosso attivo sì/no, numero da chiamare, orari di risposta (`24h` oppure es. `08:00-22:00`) | – |

L'URL del webhook Vapi da incollare nel pannello Vapi è `https://TUO-DOMINIO/webhook/vapi`.

---

## 5. GESTIONALE
Il menu a sinistra (su telefono: pulsante in alto) mostra **solo le voci consentite al tuo ruolo**. Ruoli: **ADMIN** (tutto) e **COLLABORATORE** (agenda, richieste, galleria in sola bozza, materiale, eventi, assistente).

| Voce | Cosa fa | Ruolo |
|---|---|---|
| **Dashboard** | Appuntamenti di oggi, nuove richieste, incassi del mese, prossimi eventi | tutti (incassi: solo admin) |
| **Agenda** | Calendario mensile a colori; clic su un giorno: conferma, blocca/sblocca, note | tutti |
| **Richieste** | Richieste e prenotazioni dal sito; cambio stato; «Invia riepilogo» su WhatsApp | tutti |
| **Preventivi** | Crea il preventivo (voci `descrizione;quantità;prezzo`), PDF, stato, trasformalo in fattura | admin |
| **Fatture** | Bozza, numero progressivo assegnato all'emissione, PDF elegante, stati (bozza/emessa/parziale/pagata/scaduta), stato SDI manuale. **Dati fiscali** (P.IVA, sede, IBAN, numerazione, IVA) in *Fatture > Dati fiscali* | admin |
| **Acconti** | Pagamenti parziali (metodo, data, nota), residuo e stato calcolati da soli, riepilogo incassato/da incassare | admin |
| **Clienti** | Anagrafica con indirizzo, P.IVA, CF, codice SDI, PEC | admin |
| **Galleria** | Foto con didascalia obbligatoria, tipo evento e data; partono nascoste; solo l'admin pubblica o elimina | tutti (pubblica: admin) |
| **Recensioni** | Richiesta dopo l'evento (link personale), stelle e testo, approvazione prima della pubblicazione | admin |
| **Testi del sito** | Tutti i testi del sito in un solo modulo | admin |
| **Tariffe** | Listino base; usato nei preventivi e (se «pubbliche») nella stima del configuratore | admin |
| **Materiale** | Attrezzature, quantità e stato | tutti |
| **Eventi** | Calendario eventi, attrezzatura assegnata con controllo quantità | tutti |
| **Assistente e chat** | Chiamate e chat dell'assistente AI | tutti |
| **WhatsApp** | Stato di Twilio, destinatari dei report, ultimi invii | admin |
| **Statistiche** | Incassi per mese/anno, eventi per tipo, servizi richiesti, conversione richieste → confermati | admin |
| **Report e visite** | Visite al sito e report | admin |
| **Team e contatti** | Persone mostrate nel sito e destinatari delle notifiche | admin |
| **Utenti e permessi** | Crea utenti, assegna il ruolo, disattiva, reimposta la password | admin |
| **Registro attività** | Chi ha fatto cosa e quando (azioni sensibili) | admin |
| **Impostazioni** | Dati societari, cifre del sito, SMTP, ecc. | admin |
| **Backup** | Stato dell'ultimo backup (locale + Google Drive) | admin |

**Prima del primo uso compila:** *Fatture > Dati fiscali* (P.IVA, sede, IBAN, numerazione), *Tariffe* (i prezzi), `PUBLIC_URL` nel `.env` (link delle email di recensione) e crea gli utenti collaboratori.

> ⚠️ I PDF «fattura» sono copie di cortesia: **la fattura elettronica ufficiale** si emette con il tuo software/commercialista (SDI). Dettagli in [`FATTURAZIONE-SDI.md`](FATTURAZIONE-SDI.md).

### Kit di consegna (guide PDF, QR, video)
`python -m backend.kit_consegna` genera in `consegna/` due guide PDF (Admin e Cliente), due QR da stampare, due video tutorial (verticale 9:16 e orizzontale 16:9) e un `LEGGIMI.txt`. Usa dati di prova: il database vero non viene toccato. Opzioni: `--url`, `--solo-pdf`, `--shots CARTELLA`.

---

## 6. ALTRO
- 🔐 **Cambia password** (`/admin/password`).
- 🌐 **Vedi sito**.
- **Esci** (in alto a destra).

---

## Cosa NON si modifica dal pannello (serve un tecnico o i file)
| Cosa | Dove si cambia |
|---|---|
| Email/SMTP (conferme e promemoria appuntamenti) e `OWNER_EMAIL` | file `.env` sul server (`SMTP_*`, `MAIL_FROM`, `OWNER_EMAIL`) |
| Modalità `demo` / `production`, `SECRET_KEY`, HTTPS | file `.env` |
| Testi di «Come lavoriamo» e delle FAQ, elenco tipi di evento e servizi dei form | `app/templates/index.html`, `backend/public.py` |
| Musica e voce dell'intro | `app/static/media/music.mp3`, `voce.mp3`, `voce.json` |
| Logo | `python -m backend.make_logo3d` e `app/static/img/` |
| Assistente AI esterno (facoltativo) | `.env` (`AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`) |
| Foto importate in blocco | cartella `foto/organizzate/` o `python importa_social.py` |
