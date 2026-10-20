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
| Voce | Cosa fa |
|---|---|
| 👥 **Clienti** | Anagrafica: nome, telefono, email, note |
| 🚚 **Fornitori** | Nome, categoria, contatti, note |
| 🎛️ **Magazzino** | Attrezzature: categoria (audio/luci/video), quantità, stato (disponibile / in uso / in riparazione / fuori servizio) |
| 🎤 **Eventi** | Calendario eventi: titolo, data, luogo, cliente, note + **assegna attrezzatura** all'evento (controlla le quantità) |
| 🧾 **Preventivi/Fatture** | Crea il documento (cliente, voci `descrizione;quantità;prezzo`, note), scarica il **PDF**, cambia stato, elimina |
| 💶 **Prima nota** | Entrate/uscite con totali |

> ⚠️ I PDF «fattura» sono documenti interni: **la fattura elettronica ufficiale** si emette con il tuo software/commercialista (SDI).

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
