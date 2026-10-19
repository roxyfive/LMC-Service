"""Report automatici (giornaliero / settimanale / mensile) con invio su WhatsApp.

Idempotenza: ogni invio "prenota" una riga in report_log (chiave UNIQUE, es. daily:2026-10-19). Con più worker di
gunicorn, o con cron + thread, vince il primo: nessun doppio invio. Se l'invio fallisce si ritenta (max 3 volte, ogni 30 minuti).
"""
import sqlite3
from datetime import date, datetime, timedelta, timezone

from .db import q, ex, get_db, get_setting
from . import notify, metrics

KINDS = ("daily", "weekly", "monthly")
DEFAULT_TIME = {"daily": "21:00", "weekly": "08:30", "monthly": "08:30"}
GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def stats(d1, d2):
    """Conteggi tra due giorni locali (date ISO, estremi inclusi)."""
    u1, u2 = metrics.utc_bounds(d1, d2)
    c = lambda sql: q(sql, (u1, u2), one=True)["n"]
    quotes = c("SELECT COUNT(*) n FROM quotes WHERE created >= ? AND created < ?")
    bookings = c("SELECT COUNT(*) n FROM appointments WHERE created >= ? AND created < ?")
    chat_leads = metrics.count("chat_summary", d1, d2)
    emerg = metrics.count("emergency", d1, d2)
    vcalls = metrics.count("vapi_call", d1, d2)
    return dict(
        visits=metrics.count("visit", d1, d2, distinct=True), pageviews=metrics.count("visit", d1, d2),
        quotes=quotes, bookings=bookings, chats=metrics.count("chat_msg", d1, d2, distinct=True),
        chat_leads=chat_leads, emergencies=emerg, voice_calls=vcalls,
        contacts=quotes + chat_leads + emerg + vcalls,
    )


def _n(n, one, many):
    return f"{n} {one if n == 1 else many}"


def _line(s):
    parts = [_n(s["visits"], "visita", "visite"), _n(s["contacts"], "contatto", "contatti"),
             _n(s["bookings"], "prenotazione", "prenotazioni"), _n(s["chats"], "chat con l'assistente", "chat con l'assistente")]
    if s["emergencies"]:
        parts.append(_n(s["emergencies"], "richiesta di emergenza", "richieste di emergenza"))
    return ", ".join(parts)


def _delta(a, b):
    if not b:
        return "—" if not a else "nuovo"
    p = round(100 * (a - b) / b)
    return f"{p:+d}%"


def period(kind, ref=None):
    """(d1, d2, titolo) del periodo coperto dal report di quel tipo, rispetto al giorno ref (date)."""
    ref = ref or metrics.now_local().date()
    if kind == "daily":
        return ref, ref, f"oggi ({GIORNI[ref.weekday()]} {ref:%d/%m})"
    if kind == "weekly":      # l'ultima settimana completa lun-dom
        end = ref - timedelta(days=ref.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end, f"settimana scorsa ({start:%d/%m}–{end:%d/%m})"
    first = ref.replace(day=1)   # mese precedente
    end = first - timedelta(days=1)
    return end.replace(day=1), end, f"{MESI[end.month - 1]} {end.year}"


def build_text(kind, ref=None):
    ref = ref or metrics.now_local().date()
    d1, d2, label = period(kind, ref)
    s = stats(d1.isoformat(), d2.isoformat())
    head = {"daily": "Report giornaliero", "weekly": "Report settimanale", "monthly": "Report mensile"}[kind]
    out = [f"📊 LMC Service – {head}", f"{label[0].upper() + label[1:]}: {_line(s)}."]
    if kind == "daily":
        w0 = ref - timedelta(days=ref.weekday())
        sw = stats(w0.isoformat(), ref.isoformat())
        out.append(f"Questa settimana (lun–oggi): {_line(sw)}.")
    else:
        span = (d2 - d1).days + 1
        if kind == "weekly":
            p2, p1 = d1 - timedelta(days=1), d1 - timedelta(days=span)
        else:
            p2 = d1 - timedelta(days=1)
            p1 = p2.replace(day=1)
        sp = stats(p1.isoformat(), p2.isoformat())
        out.append("Rispetto al periodo precedente: visite " + _delta(s["visits"], sp["visits"]) + ", contatti " + _delta(s["contacts"], sp["contacts"])
                   + ", prenotazioni " + _delta(s["bookings"], sp["bookings"]) + ".")
    return "\n".join(out)


# ---------- pianificazione ----------
def _parse_time(v, default):
    try:
        h, m = (v or default).split(":")
        return int(h), int(m)
    except (ValueError, AttributeError):
        h, m = default.split(":")
        return int(h), int(m)


def enabled(kind):
    return (get_setting(f"report_{kind}_on", "1" if kind == "daily" else "0") or "0") == "1"


def due(now=None):
    """Elenco (kind, chiave) dei report da inviare adesso, in base a orario, giorno e interruttori in admin."""
    now = now or metrics.now_local()
    out = []
    for kind in KINDS:
        if not enabled(kind):
            continue
        h, m = _parse_time(get_setting(f"report_{kind}_time", ""), DEFAULT_TIME[kind])
        if (now.hour, now.minute) < (h, m):
            continue
        if kind == "daily":
            out.append((kind, f"daily:{now.date().isoformat()}"))
        elif kind == "weekly" and now.weekday() == 0:
            y, w, _ = now.isocalendar()
            out.append((kind, f"weekly:{y}-W{w:02d}"))
        elif kind == "monthly" and now.day == 1:
            out.append((kind, f"monthly:{now.year}-{now.month:02d}"))
    return out


def _claim(key, kind):
    """True se questo processo può inviare. Prima volta: INSERT; ritentativi: solo se fallito, <3 prove, >30 min fa."""
    db = get_db()
    try:
        db.execute("INSERT INTO report_log(key,kind,tries) VALUES(?,?,1)", (key, kind))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
    limit = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    cur = db.execute("UPDATE report_log SET tries=tries+1, sent_at=CURRENT_TIMESTAMP WHERE key=? AND ok=0 AND tries<3 AND sent_at<?", (key, limit))
    db.commit()
    return cur.rowcount == 1


def deliver(kind, ref=None, key=None):
    text = build_text(kind, ref)
    nums = notify.recipients(f"report:{kind}")
    if not nums:
        res = dict(configured=notify.twilio_ready(), sent=0, failed=0, errors=["nessun destinatario con numero valido"])
    else:
        res = notify.send_many(nums, text, f"report:{kind}")
    ok = res["sent"] > 0
    detail = f"inviato a {res['sent']}/{res.get('recipients', len(nums))}" + (f"; errori: {'; '.join(res['errors'][:2])}" if res["errors"] else "")
    if key:
        ex("UPDATE report_log SET ok=?, detail=? WHERE key=?", (int(ok), detail[:300], key))
    return ok, detail, text


def run_due(now=None):
    """Da chiamare ogni minuto circa (thread) o da cron (`python run.py --report`). Ritorna i report inviati."""
    if not notify.twilio_ready():      # senza Twilio non si "consuma" la finestra di invio: parte appena configurato
        return []
    sent = []
    for kind, key in due(now):
        if _claim(key, kind):
            ok, detail, _t = deliver(kind, (now or metrics.now_local()).date(), key)
            sent.append((key, ok, detail))
    return sent


def send_now(kind):
    """Invio manuale dall'admin (non occupa lo slot automatico)."""
    key = f"manual:{kind}:{metrics.now_local():%Y%m%d%H%M%S}"
    ex("INSERT INTO report_log(key,kind,tries) VALUES(?,?,1)", (key, kind))
    return deliver(kind, None, key)


def recent_log(n=12):
    return q("SELECT * FROM report_log ORDER BY id DESC LIMIT ?", (n,))
