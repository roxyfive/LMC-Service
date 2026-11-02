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


def _footer():
    from .db import get_setting
    base = (os.getenv("PUBLIC_URL", "") or get_setting("sito_url", "") or "").strip().rstrip("/")
    link = f"{base}/privacy" if base else "la pagina «Informativa privacy» del nostro sito"
    return ("\n\n--\nTrattiamo i tuoi dati solo per gestire questa richiesta; non li cediamo a terzi per pubblicità. "
            f"Informativa e diritti: {link}. Se non vuoi ricevere altre email da noi, rispondi a questo messaggio.")


def send_cliente(to, subject, body):
    """Email al cliente: come send_mail, con in fondo la nota privacy e come chiedere di non riceverne altre."""
    return send_mail(to, subject, body + _footer())
