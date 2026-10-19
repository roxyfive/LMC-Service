import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from .config import DATA


def _log(text):
    with open(DATA / "outbox.log", "a", encoding="utf-8") as f:
        f.write(text)


def send_mail(to, subject, body):
    """Invia via SMTP se configurato, altrimenti scrive in data/outbox.log."""
    if not to:
        return False
    host = os.getenv("SMTP_HOST")
    try:
        if not host:
            _log(f"--- {datetime.now():%Y-%m-%d %H:%M} A:{to}\nOggetto: {subject}\n{body}\n\n")
            return True
        m = EmailMessage()
        m["From"] = os.getenv("MAIL_FROM") or os.getenv("SMTP_USER", "")
        m["To"] = to
        m["Subject"] = subject
        m.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
            s.starttls()
            s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""))
            s.send_message(m)
        return True
    except Exception as e:
        _log(f"ERRORE invio a {to}: {e}\n")
        return False
