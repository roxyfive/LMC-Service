"""Avviso di backup fallito/mancante: email al titolare (OWNER_EMAIL, via SMTP del sito) e WhatsApp a chi è di turno.
Uso: python deploy/backup-alert.py "Oggetto" "Messaggio"   (lo lancia backup.sh; gira come utente del sito)"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["LMC_NO_BG"] = "1"                   # nessun thread di sfondo per un avviso al volo
subject = sys.argv[1] if len(sys.argv) > 1 else "Backup LMC Service"
msg = sys.argv[2] if len(sys.argv) > 2 else ""

from backend import create_app, notify          # noqa: E402
from backend.mailer import send_mail           # noqa: E402

app = create_app()
with app.app_context():
    sent = []
    owner = os.getenv("OWNER_EMAIL")
    if owner and send_mail(owner, f"⚠️ {subject}", f"{msg}\n\nControlla sul server: tail -n 50 /var/log/lmc-backup.log\nGuida: docs/DEPLOY.md (Parte 4)."):
        sent.append("email")
    try:
        if notify.twilio_ready():
            r = notify.send_many(notify.recipients("duty"), f"⚠️ LMC Service – {subject}: {msg}"[:900], "backup")
            if r["sent"]:
                sent.append("whatsapp")
    except Exception as e:                       # l'avviso non deve mai bloccare il backup
        print("WhatsApp non inviato:", e)
    print("avviso inviato via:", ", ".join(sent) or "nessun canale configurato (vedi data/outbox.log)")
