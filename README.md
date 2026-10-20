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
Tema bianco puro (#ffffff, sezioni alterne #fafafa), antracite, oro e blu notte; nessun effetto scintillante. Titoli Montserrat ExtraBold, numeri e etichette Space Grotesk, testi Inter (font locali in `app/static/fonts/`, licenza OFL).
L'intro usa musica + didascalie animate: **nessuna voce sintetica del browser**. `app/static/media/voce.mp3` (voce italiana ElevenLabs, 44 s) è già inclusa e `voce.json` ne sincronizza le slide;
per cambiarla vedi `docs/voce-script.md`. Test audio in un vero browser: `python -m tests.test_audio`. Analisi e ricerca del redesign: `docs/ANALISI-DESIGN.md`. Con `APP_MODE=demo` i testi/foto generici sono marcati DEMO.

## ⚠️ Foto DEMO da sostituire
Le foto in `foto/organizzate/` (1 hero, 1 galleria, 3 installazioni) sono **immagini demo temporanee**, non lavori di LMC Service
(vedi `foto/organizzate/CREDITI.md`). Per sostituirle: copia le foto vere nella stessa cartella **con lo stesso nome**
(es. `hero/hero-01.jpg`) e riavvia il sito, oppure metti il materiale del cliente in `foto/da_social/` e lancia
`python importa_social.py foto/da_social`. Dettagli in `foto/organizzate/LEGGIMI.md`.

## Foto e video reali da Instagram/Facebook
`python importa_social.py foto/da_social/*.zip` → estrae, rinomina e smista in `foto/organizzate/`; poi riavvia il sito
(o Admin › Foto › Sincronizza). Dettagli in `foto/organizzate/LEGGIMI.md`. Test: `python -m tests.test_foto`

## Rigenerare materiali
`python -m backend.make_assets` (loghi/icone/musica) · `python video/make_video.py` · `python docs/make_pdf.py`

## Pubblicazione
**Pubblicazione online (VPS IONOS):** `docs/DEPLOY.md` (installazione guidata con `deploy/setup-vps.sh`: gunicorn + systemd + nginx + HTTPS + backup notturno).
Prima del go-live: `docs/CHECKLIST-GO-LIVE.md` (cosa compilare) e `docs/GUIDA-ADMIN.md` (tutto ciò che si gestisce dal pannello).
Controllo «sito attivo»: `GET /health` → `200 {"status":"ok"}`. Test di preparazione al go-live: `python -m tests.test_deploy`.
