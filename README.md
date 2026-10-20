# LMC Service – La Music Company Service (Napoli)

Vetrina PWA + prenotazioni + preventivi + admin + gestionale base + assistente AI.
Stack: Flask + SQLite (schema SQL portabile) · Gunicorn/Nginx sul VPS.

## Avvio locale (un solo comando)
```
avvia.bat            (Windows: crea .venv, installa, apre il browser)
```
oppure `pip install -r requirements.txt && python run.py` → http://localhost:5000 · admin: /admin
Al primo avvio, senza `ADMIN_PASSWORD` in `.env`, la password admin viene stampata **una sola volta** nel terminale.

## Modalità
`.env` → `APP_MODE=demo` (dati finti, per mostrarlo) | `production` (dati reali). Vedi `.env.example`.

## Cartelle
- `app/` template e statici (PWA, intro, CSS/JS) · `backend/` Flask, DB, admin, gestionale, AI, PDF
- `contenuti/` testi e fonti · `foto/organizzate/{hero,galleria,installazioni,video}` (foto e video reali, pubblicati in automatico all'avvio) · `foto/da_social/` (ZIP Meta, mai su git) · `data/` DB + upload (backup)
- `docs/` guida deploy, PDF clienti/admin, kit social, scaletta video · `video/` intro 16:9 e 9:16, tutorial
- `tests/test_e2e.py` test end-to-end: `python -m tests.test_e2e`

## WhatsApp, voce, report ed emergenza
Assistente vocale (voce del browser o Vapi), riepilogo chat su WhatsApp (Twilio), report giornaliero/settimanale/mensile, pulsante Emergenza 24h.
Tutto si configura da **Admin › Impostazioni** (o `.env`): vedi `docs/CONFIGURAZIONE-API.md`. Pagina **Admin › Report** per i numeri. Proposte future: `docs/PROPOSTE.md`.
Logo 3D: `python -m backend.make_logo3d` (richiede scipy e fonttools; non serve per far girare il sito).

## Team e Contatti (da admin)
Admin › **Team e Contatti**: nome, ruolo, telefono, email, nota, visibilità e ordine di ogni collaboratore. Si salva nel database: compare
nella sezione Contatti del sito e l'assistente risponde con questi dati ("numero di Pasquale?"). Precaricato: Pasquale (titolare, +39 366 178 2548, aperto 24 ore).
Telefono principale, WhatsApp e orari si modificano in Admin › Testi. Numeri della sezione "In cifre": DEMO finché non si imposta `stats` nelle impostazioni.

## Design e voce
Tema scuro morbido (grigio-nerastro): sfondo #16161c, sezioni alterne #1c1c22, testi bianchi, contorni e accenti rossi (#e11d14), tasto Emergenza rosso vivo; vale anche per l'intro (solo colori). Titoli Montserrat ExtraBold, numeri e etichette Space Grotesk, testi Inter (font locali in `app/static/fonts/`, licenza OFL). Il tema è l'ultimo blocco di `app/static/css/site.css` («TEMA NERO»).
L'intro usa musica + didascalie animate: **nessuna voce sintetica del browser**. `app/static/media/voce.mp3` (voce italiana ElevenLabs, 44 s) è già inclusa e `voce.json` ne sincronizza le slide;
per cambiarla vedi `docs/voce-script.md`. Test audio in un vero browser: `python -m tests.test_audio`. Analisi e ricerca del redesign: `docs/ANALISI-DESIGN.md`. Con `APP_MODE=demo` i testi/foto generici sono marcati DEMO.

## ⚠️ Foto DEMO da sostituire
Le foto in `foto/organizzate/` sono **le foto reali del cliente** (25 foto + 6 video, credito Merette Uiterwaal, uso autorizzato sul sito del cliente: vedi `CREDITI.md`).
Prima della pubblicazione sono state migliorate con `python -m backend.enhance_foto` (orientamento, esposizione, colore, rumore, nitidezza; originali in `foto/_originali/`, non su git).
Per aggiungerne: copiale nelle sottocartelle, lancia `python -m backend.enhance_foto`, riavvia il sito (o Admin › Foto › Sincronizza); sulla VPS basta `deploy/aggiorna.sh`. Dettagli in `foto/organizzate/LEGGIMI.md`.

## Foto e video reali da Instagram/Facebook
`python importa_social.py foto/da_social/*.zip` → estrae, rinomina e smista in `foto/organizzate/`; poi riavvia il sito
(o Admin › Foto › Sincronizza). Dettagli in `foto/organizzate/LEGGIMI.md`. Test: `python -m tests.test_foto`

## Rigenerare materiali
`python -m backend.make_assets` (loghi/icone/musica) · `python video/make_video.py` · `python docs/make_pdf.py`

## Pubblicazione
**Pubblicazione online (VPS IONOS):** `docs/DEPLOY.md` (installazione guidata con `deploy/setup-vps.sh`: gunicorn + systemd + nginx + HTTPS + backup notturno).
Prima del go-live: `docs/CHECKLIST-GO-LIVE.md` (cosa compilare) e `docs/GUIDA-ADMIN.md` (tutto ciò che si gestisce dal pannello).
Backup: notturno, cifrato, con copia verificata su IONOS Object Storage e avvisi (`docs/DEPLOY.md` Parte 4). Test: `python -m tests.test_backup_cloud` (usa un S3 emulato, serve `pip install "moto[server]" rclone-bin`).
Controllo «sito attivo»: `GET /health` → `200 {"status":"ok"}`. Test di preparazione al go-live: `python -m tests.test_deploy`.
