"""Conteggi anonimi per i report: visite, chat, azioni. Nessun cookie, nessun IP salvato.

Il visitatore è un hash giornaliero (sale casuale salvato nel database + giorno + IP + browser):
serve solo a contare le visite uniche del giorno e non permette di seguire una persona da un giorno all'altro.
"""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from .db import q, ex, get_setting, set_setting

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Rome")
except Exception:   # tzdata assente (es. Windows senza pacchetto tzdata): approssima con UTC+1
    TZ = timezone(timedelta(hours=1))

BOT = ("bot", "crawl", "spider", "slurp", "preview", "facebookexternalhit", "headless", "lighthouse", "monitor", "curl", "wget", "python-requests")


def now_local():
    return datetime.now(TZ)


def today():
    return now_local().date().isoformat()


def _salt():
    s = get_setting("visit_salt", "")
    if not s:
        s = secrets.token_hex(16)
        set_setting("visit_salt", s)
    return s


def visitor_hash(req):
    ip = (req.remote_addr or "")
    ua = req.headers.get("User-Agent", "")
    return hashlib.sha256(f"{_salt()}|{today()}|{ip}|{ua}".encode()).hexdigest()[:16]


def is_bot(req):
    ua = req.headers.get("User-Agent", "").lower()
    return not ua or any(b in ua for b in BOT)


def track(kind, ref="", day=None):
    ex("INSERT INTO stats_events(day,kind,ref) VALUES(?,?,?)", (day or today(), kind, ref))


def track_visit(req):
    if not is_bot(req):
        track("visit", visitor_hash(req))


def count(kind, d1, d2, distinct=False):
    col = "COUNT(DISTINCT ref)" if distinct else "COUNT(*)"
    return q(f"SELECT {col} n FROM stats_events WHERE kind=? AND day BETWEEN ? AND ?", (kind, d1, d2), one=True)["n"]


def utc_bounds(d1, d2):
    """Giorni locali (date ISO) -> stringhe UTC 'YYYY-MM-DD HH:MM:SS' per confrontarle con i campi created."""
    a = datetime.fromisoformat(d1).replace(tzinfo=TZ).astimezone(timezone.utc)
    b = (datetime.fromisoformat(d2) + timedelta(days=1)).replace(tzinfo=TZ).astimezone(timezone.utc)
    f = "%Y-%m-%d %H:%M:%S"
    return a.strftime(f), b.strftime(f)
