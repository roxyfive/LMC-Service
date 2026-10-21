# Checklist prima di andare online – LMC Service

Legenda — **🔴 Bloccante**: non pubblicare senza · **🟠 Consigliato**: il sito funziona ma perde valore / affidabilità · **🟢 Facoltativo**.
Percorsi: «Admin › X» = menu a sinistra del pannello `/admin`. «`.env`» = file di configurazione sul server (`/srv/lmc/.env`).
La guida di tutto il pannello è in `docs/GUIDA-ADMIN.md`, il deploy in `docs/DEPLOY.md`.

## A. Dati e contenuti da compilare

| # | Cosa manca | Dove si inserisce | Stato oggi | |
|---|---|---|---|---|
| 1 | **Foto e video reali** del cliente (25 foto + 6 video, credito Merette Uiterwaal): già in `foto/organizzate/` e pubblicate. Mancano foto di **videosorveglianza** e **ledwall** (le due card skill sono senza immagine finché non arrivano). Tieni `foto/organizzate/CREDITI.md` | Admin › Foto e video, oppure cartelle `foto/organizzate/{hero,galleria,installazioni,video}` + «Sincronizza» | Reali ✅ (chiedere al cliente le foto mancanti) | 🟠 |
| 2 | **P.IVA e dati societari** (ragione sociale, P.IVA, sede legale): obbligatori per un sito commerciale | Admin › Testi › *Dati societari nel footer* (compare nel footer e sull'intestazione dei PDF) | Vuoto | 🔴 |
| 3 | **Informativa privacy completa** (fornitori, sede dei dati, conservazione, basi giuridiche) con il consulente. Il testo base c'è, ma è provvisorio | Admin › Testi › *Informativa privacy – testo principale* e *– dettagli* (il segnaposto «[DA COMPLETARE]» non viene mai mostrato al pubblico) | Testo base | 🔴 |
| 4 | **Email di contatto del sito** | Admin › Testi › *Email* | `lamusiccompany.24@gmail.com` già inserita (sito, Team, footer, assistente) ✅ | 🟢 |
| 5 | **Disponibilità appuntamenti reali** (fasce e giorni di chiusura) | Admin › Disponibilità | Default lun–ven 10–13 / 16–19 | 🔴 se si accettano prenotazioni |
| 6 | **Testi dei servizi («skill») da confermare** con Pasquale (4 servizi) | Admin › Testi › *Servizi* | Indicativi | 🟠 |
| 7 | **Testi «Come lavoriamo» e FAQ** da far approvare (sono nel codice) | `app/templates/index.html` (chiedere allo sviluppatore) | Indicativi | 🟠 |
| 8 | **Recensioni vere** dei clienti (con il loro permesso) | Admin › Dicono di noi | Nessuna: in produzione la sezione resta nascosta | 🟠 |
| 9 | **Cifre vere** (eventi realizzati, anni di attività…) | Admin › Testi › *Cifre in evidenza* | Vuote: in produzione compare solo «Aperti 24 ore su 24» | 🟠 |
| 10 | **Nome e titolare, città, data di fondazione** da verificare | Admin › Testi (gruppo Identità) | Compilati (verificare) | 🟠 |
| 11 | **Telefono, WhatsApp, orari, zone** da verificare | Admin › Testi (+39 366 178 2548, «Aperto 24 ore») | Compilati | 🟠 |
| 12 | **URL social**: Instagram, Facebook (+ nome pagina), **TikTok**, **Sito ufficiale** (dominio definitivo) | Admin › Testi › Social | Instagram/Facebook/TikTok presenti dal Linktree (verificare che i link aprano le pagine giuste); *Sito ufficiale* vuoto | 🟠 |
| 13 | **Team**: persone reali, numeri, chi è «di turno» e chi riceve le notifiche | Admin › Team e Contatti | Solo Pasquale | 🟠 |
| 14 | **Licenza voce/musica dell'intro** (voce ElevenLabs: uso commerciale secondo il piano; musica sintetizzata dal progetto) | `app/static/media/voce.mp3`, `music.mp3` | Da verificare | 🟠 |

## B. Accessi e chiavi

| # | Cosa | Dove | Bloccante |
|---|---|---|---|
| 15 | **Cambiare la password admin** al primo accesso e **cancellare `ADMIN_PASSWORD` dal `.env`** (l'installer lo fa da solo) | Admin › 🔐 Cambia password | 🔴 |
| 16 | **`APP_MODE=production`**, `SECRET_KEY` casuale, `TRUST_PROXY=1`, `COOKIE_SECURE=1` | `.env` (modello: `deploy/env.production.example`) | 🔴 |
| 17 | **Email in uscita (SMTP)** e `OWNER_EMAIL`: senza, le conferme/promemoria degli appuntamenti NON partono (finiscono in `data/outbox.log`) e Pasquale non riceve le notifiche email | `.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `OWNER_EMAIL` (con IONOS Mail: `smtp.ionos.it`, porta 587) | 🔴 se si usano le prenotazioni |
| 18 | **WhatsApp (Twilio)**: Account SID, Auth Token, numero mittente, destinatari | Admin › Impostazioni › WhatsApp / Twilio (poi «Verifica credenziali» e «Messaggio di prova») | 🟠 (senza: nessuna notifica/report WhatsApp, il sito funziona) |
| 19 | **Vapi (voce AI)**: Public Key, Assistant ID, Assistant ID emergenza, Secret webhook; sul pannello Vapi incolla `https://DOMINIO/webhook/vapi` | Admin › Impostazioni › Assistente vocale | 🟢 (senza: il tasto «Emergenza – Parla con l'AI» chiama direttamente Pasquale) |
| 20 | **Emergenza 24h**: numero e orari di risposta; almeno una persona «di turno» | Admin › Impostazioni › Emergenza 24h + Team | 🟠 |
| 21 | **Report automatici**: attivare giornaliero/settimanale/mensile e scegliere i destinatari | Admin › Impostazioni › Report automatici | 🟢 |
| 22 | **Assistente AI esterno** (modello più «intelligente») | `.env`: `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` | 🟢 (senza: risposte dai dati del sito) |

## C. Infrastruttura

| # | Cosa | Dove | Bloccante |
|---|---|---|---|
| 23 | **Dominio** con record DNS **A** verso l'IP della VPS (e **AAAA** se usi IPv6) | Pannello domini IONOS | 🔴 |
| 24 | **HTTPS** attivo (Let's Encrypt): serve per microfono, PWA e webhook | `deploy/setup-vps.sh` / `certbot` | 🔴 |
| 25 | **Backup notturno attivo e cifrato**, **password di cifratura salvata fuori dal VPS**, **copia su IONOS Object Storage** (bucket + chiavi in `deploy/lmc-backup.conf`), prova di copia verificata («copia su IONOS ok e verificata») e **prova di ripristino** | `docs/DEPLOY.md` Parte 4 (sul server condiviso: Parte 4.9, backup LMC via guard su Google Drive) | 🔴 la password e il backup locale; 🟠 la copia IONOS |
| 26 | **Monitoraggio** `https://DOMINIO/health` (es. UptimeRobot, controllo ogni 5 min, avviso via email) | servizio di monitoraggio | 🟠 |
| 27 | Test finale su telefono: intro, form (invia un preventivo di prova), prenotazione, chat, microfono, tasto emergenza | – | 🔴 |
| 28 | Registrare il sito su **Google Search Console** (sitemap: `https://DOMINIO/sitemap.xml`) e creare/aggiornare la scheda **Google Business Profile** | Google | 🟢 |

## D. Da sapere
- **Fatture**: i PDF «fattura» dell'admin sono documenti interni. La **fattura elettronica** (SDI) si emette con il vostro software/commercialista.
- **Cookie**: il sito usa solo un cookie tecnico di sessione e statistiche anonime senza tracciamento; verifica con il consulente se serve altro.
- **Foto e credits**: le foto sono del cliente (La Music Company Service), fotografa Merette Uiterwaal, uso autorizzato sul sito del cliente: tieni `foto/organizzate/CREDITI.md`. Le foto sono migliorate con `python -m backend.enhance_foto` (gli originali stanno in `foto/_originali/`, solo sul PC, non su git).
- **Prima del lancio** fai un backup manuale (`sudo /srv/lmc/deploy/backup.sh`) e prova un ripristino su una cartella di prova (vedi DEPLOY).
