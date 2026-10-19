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

## Foto e video reali da Instagram/Facebook
`python importa_social.py foto/da_social/*.zip` → estrae, rinomina e smista in `foto/organizzate/`; poi riavvia il sito
(o Admin › Foto › Sincronizza). Dettagli in `foto/organizzate/LEGGIMI.md`. Test: `python -m tests.test_foto`

## Rigenerare materiali
`python -m backend.make_assets` (loghi/icone/musica) · `python video/make_video.py` · `python docs/make_pdf.py`

## Pubblicazione
Vedi `docs/DEPLOY.md` (Nginx, systemd, SSL, backup).
