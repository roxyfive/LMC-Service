import os
import re
import json
import secrets
import urllib.parse
from datetime import date, datetime, timedelta
from flask import (Blueprint, render_template, request, jsonify, send_from_directory, abort,
                   Response, url_for, session)
from .db import q, ex, get_setting, all_settings
from .config import UPLOADS, CATEGORIES
from .security import check_csrf, csrf_token, current_user
from .mailer import send_mail
from . import ai
from . import vetrina
from . import notify, metrics

bp = Blueprint("pub", __name__)
FILE_RE = re.compile(r"^[0-9a-f]{32}(_\d+)?\.(webp|mp4|webm)$")
EVENT_TYPES = ["Matrimonio", "Festa privata", "Evento aziendale / Meeting", "Concerto / Show", "Discoteca / Locale", "Altro"]
SERVICES = ["Audio", "Luci", "Video", "Allestimenti", "Videosorveglianza", "Progettazione"]


def _clean(v, n=300):
    return (v or "").strip()[:n]


def _valid_email(e):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e or ""))


def _valid_phone(p):
    return len(re.sub(r"\D", "", p or "")) >= 6


def free_slots(day):
    try:
        d = date.fromisoformat(day)
    except ValueError:
        return []
    if d <= date.today():
        return []
    if q("SELECT 1 FROM closures WHERE date=?", (day,), one=True):
        return []
    step = int(get_setting("slot_minutes", "60") or 60)
    taken = {r["slot_time"] for r in q(
        "SELECT slot_time FROM appointments WHERE slot_date=? AND status!='annullato'", (day,))}
    out = []
    for a in q("SELECT start,end FROM availability WHERE weekday=? ORDER BY start", (d.weekday(),)):
        t = datetime.strptime(a["start"], "%H:%M")
        end = datetime.strptime(a["end"], "%H:%M")
        while t + timedelta(minutes=step) <= end:
            hh = t.strftime("%H:%M")
            if hh not in taken:
                out.append(hh)
            t += timedelta(minutes=step)
    return out


def ctx():
    s = all_settings()
    try:
        s["servizi_list"] = json.loads(s.get("servizi", "[]") or "[]")
    except ValueError:
        s["servizi_list"] = []
    try:
        s["intro_list"] = json.loads(s.get("intro_righe", "[]") or "[]")
    except ValueError:
        s["intro_list"] = []
    return s


@bp.route("/")
def index():
    s = ctx()
    try:
        metrics.track_visit(request)
    except Exception:
        pass
    media = q("SELECT * FROM media WHERE hidden=0 ORDER BY featured DESC, sort, id")
    gallery = [m for m in media if m["show_gallery"] and m["kind"] == "image"]
    home = [m for m in media if m["show_home"] and m["kind"] == "image"]
    intro = [m for m in media if m["show_intro"] and m["kind"] == "image"] or home[:6]
    videos = [m for m in media if m["kind"] == "video"]
    hero = next((m for m in media if m["featured"] and m["kind"] == "image"), None)
    reviews = q("SELECT * FROM reviews WHERE hidden=0 AND status='approvata' ORDER BY id DESC")
    s["team"] = q("SELECT * FROM team WHERE visible='si' ORDER BY sort, id")
    v = vetrina.build(media)
    # una foto compare UNA sola volta nella home: quelle già usate come immagine di una card «skill» non si ripetono in galleria
    taken = v["skill_ids"] | {m["id"] for m in v["hero_slides"]}
    rest = [m for m in gallery if m["id"] not in taken]
    gallery = rest if len(rest) >= 4 else gallery          # con pochissime foto la galleria non si svuota
    used = {m["category"] for m in gallery}
    v["stats"] = vetrina.stats(s, os.getenv("APP_MODE", "demo") == "demo")
    on, number, hours = _emergency_cfg()
    emg = dict(on=bool(on and notify.normalize_number(number)), number=notify.normalize_number(number), open_now=_open_now(hours), hours=hours)
    return render_template("index.html", emg=emg, s=s, gallery=gallery, home=home, intro=intro, videos=videos, v=v,
                           hero=hero, reviews=reviews, cats=[c for c in CATEGORIES if c in used],
                           has_placeholder=any(m["placeholder"] for m in gallery), event_types=EVENT_TYPES,
                           services=SERVICES, demo=(os.getenv("APP_MODE", "demo") == "demo"))


@bp.route("/media/<name>")
def media_file(name):
    if not FILE_RE.match(name):
        abort(404)
    base = name.split(".")[0].split("_")[0]
    row = q("SELECT hidden FROM media WHERE filename=?", (base,), one=True)
    if not row or (row["hidden"] and not bool(current_user())):
        abort(404)
    resp = send_from_directory(UPLOADS, name)
    resp.headers["Cache-Control"] = "public, max-age=604800"
    return resp


@bp.route("/api/slots")
def api_slots():
    return jsonify(free_slots(request.args.get("date", "")))


@bp.route("/api/appuntamento", methods=["POST"])
def api_appuntamento():
    check_csrf()
    d = request.get_json(silent=True) or {}
    name, phone, email = _clean(d.get("name"), 80), _clean(d.get("phone"), 30), _clean(d.get("email"), 120)
    if not name or not _valid_phone(phone) or not _valid_email(email):
        return jsonify(error="Compila nome, telefono ed email validi."), 400
    if not d.get("consent"):
        return jsonify(error="Serve il consenso al trattamento dei dati."), 400
    day, hh = _clean(d.get("date"), 10), _clean(d.get("time"), 5)
    if hh not in free_slots(day):
        return jsonify(error="Questo orario non è più disponibile. Scegline un altro."), 409
    token = secrets.token_urlsafe(16)
    ex("""INSERT INTO appointments(token,name,phone,email,event_type,event_date,notes,slot_date,slot_time,consent)
          VALUES(?,?,?,?,?,?,?,?,?,1)""",
       (token, name, phone, email, _clean(d.get("event_type"), 60), _clean(d.get("event_date"), 10),
        _clean(d.get("notes"), 800), day, hh))
    link = request.host_url.rstrip("/") + url_for("pub.manage", token=token)
    send_mail(email, "Appuntamento ricevuto – LMC Service",
              f"Ciao {name},\nabbiamo ricevuto la tua richiesta per il {day} alle {hh}.\n"
              f"Il titolare la confermerà a breve.\nModifica o annulla qui: {link}\n\nLMC Service")
    _notify_request(f"📅 Nuova richiesta di appuntamento dal sito\n{name} – {phone}\n{day} alle {hh}\nEvento: {d.get('event_type')} il {d.get('event_date')}")
    send_mail(os.getenv("OWNER_EMAIL"), f"Nuovo appuntamento: {name} {day} {hh}",
              f"{name} – {phone} – {email}\nEvento: {d.get('event_type')} il {d.get('event_date')}\nNote: {d.get('notes')}")
    return jsonify(ok=True, token=token, link=link)


@bp.route("/appuntamento/<token>", methods=["GET", "POST"])
def manage(token):
    a = q("SELECT * FROM appointments WHERE token=?", (token,), one=True)
    if not a:
        abort(404)
    msg = ""
    if request.method == "POST":
        check_csrf()
        act = request.form.get("act")
        if act == "annulla":
            ex("UPDATE appointments SET status='annullato' WHERE id=?", (a["id"],))
            send_mail(os.getenv("OWNER_EMAIL"), f"Appuntamento annullato: {a['name']}",
                      f"{a['name']} ha annullato {a['slot_date']} {a['slot_time']}")
            msg = "Appuntamento annullato."
        elif act == "modifica":
            day, hh = _clean(request.form.get("date"), 10), _clean(request.form.get("time"), 5)
            if hh in free_slots(day):
                ex("UPDATE appointments SET slot_date=?,slot_time=?,status='in attesa',reminded=0 WHERE id=?",
                   (day, hh, a["id"]))
                send_mail(os.getenv("OWNER_EMAIL"), f"Appuntamento spostato: {a['name']}", f"Nuovo orario {day} {hh}")
                msg = "Appuntamento spostato."
            else:
                msg = "Orario non disponibile."
        a = q("SELECT * FROM appointments WHERE token=?", (token,), one=True)
    return render_template("manage.html", a=a, s=ctx(), msg=msg)


@bp.route("/api/preventivo", methods=["POST"])
def api_preventivo():
    check_csrf()
    d = request.get_json(silent=True) or {}
    name, phone, email = _clean(d.get("name"), 80), _clean(d.get("phone"), 30), _clean(d.get("email"), 120)
    if not name or not _valid_phone(phone) or not _valid_email(email):
        return jsonify(error="Compila nome, telefono ed email validi."), 400
    if not d.get("consent"):
        return jsonify(error="Serve il consenso al trattamento dei dati."), 400
    services = ", ".join(x for x in (d.get("services") or []) if x in SERVICES)
    ex("""INSERT INTO quotes(name,phone,email,event_type,event_date,place,guests,services,notes,consent)
          VALUES(?,?,?,?,?,?,?,?,?,1)""",
       (name, phone, email, _clean(d.get("event_type"), 60), _clean(d.get("event_date"), 10),
        _clean(d.get("place"), 120), _clean(d.get("guests"), 10), services, _clean(d.get("notes"), 800)))
    send_mail(email, "Richiesta preventivo ricevuta – LMC Service",
              f"Ciao {name},\nabbiamo ricevuto la tua richiesta di preventivo. Ti risponderemo al più presto.\n\nLMC Service")
    _notify_request(f"🆕 Nuovo preventivo dal sito\n{name} – {phone}\n{d.get('event_type')} il {d.get('event_date')} a {d.get('place')}, {d.get('guests')} ospiti\nServizi: {services}")
    send_mail(os.getenv("OWNER_EMAIL"), f"Nuovo preventivo: {name}",
              f"{name} – {phone} – {email}\n{d.get('event_type')} il {d.get('event_date')} a {d.get('place')}, "
              f"{d.get('guests')} ospiti\nServizi: {services}\n{d.get('notes')}")
    return jsonify(ok=True)


def _notify_request(text):
    """Avviso WhatsApp al team per nuovi preventivi/appuntamenti (se Twilio è configurato e l'interruttore è attivo)."""
    try:
        if notify.twilio_ready() and notify.flag("wa_notify_requests", "1"):
            notify.fire(text, "request")
    except Exception:
        pass


# ---------- configurazione pubblica per il widget (nessun segreto) ----------
def _emergency_cfg():
    on = get_setting("emergency_on", "1") == "1"
    number = get_setting("emergency_number", "").strip()
    if not number:
        duty = q("SELECT phone FROM team WHERE phone!='' ORDER BY (on_duty='si') DESC, sort, id LIMIT 1", one=True)
        number = duty["phone"] if duty else get_setting("telefono", "")
    hours = (get_setting("emergency_hours", "24h") or "24h").strip().lower()
    return on, number, hours


def _open_now(hours):
    if hours in ("", "24h", "24", "24/7", "h24"):
        return True
    m = re.match(r"^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$", hours)
    if not m:
        return True
    a, b = int(m[1]) * 60 + int(m[2]), int(m[3]) * 60 + int(m[4])
    n = metrics.now_local()
    cur = n.hour * 60 + n.minute
    return (a <= cur < b) if a <= b else (cur >= a or cur < b)


@bp.route("/api/config")
def api_config():
    on, number, hours = _emergency_cfg()
    num = notify.normalize_number(number)
    r = jsonify(
        wa_ready=notify.twilio_ready(), admin=bool(current_user()),
        vapi=dict(enabled=notify.vapi_ready(), public_key=notify.cfg("vapi_public_key"), assistant_id=notify.cfg("vapi_assistant_id"),
                  emergency_assistant_id=notify.cfg("vapi_emergency_assistant_id")),
        suggestions=ai.suggestions(),
        emergency=dict(on=bool(on and num), number=num, hours=hours, open_now=_open_now(hours)),
        contact_wa=notify.normalize_number(get_setting("whatsapp", "")) or num)
    r.headers["Cache-Control"] = "no-store"
    return r


def _chat_summary(msgs, name, phone):
    mine = [m["content"] for m in msgs if m["role"] == "user"]
    txt = " | ".join(mine[-6:])[:600] or "(nessun messaggio)"
    allt = " ".join(mine).lower()
    intent = "preventivo" if "preventiv" in allt else ("prenotazione" if "prenot" in allt or "appuntament" in allt else "informazioni")
    now = metrics.now_local()
    return (f"💬 Nuova richiesta dall'assistente del sito\nNome: {name or 'non indicato'}\nTelefono: {phone}\n"
            f"Data: {now:%d/%m/%Y %H:%M}\nTipo: {intent}\nRichiesta: {txt}")


def _wa_cap_ok():
    cap = int(get_setting("wa_public_cap", "60") or 60)
    n = q("SELECT COUNT(*) n FROM wa_log WHERE kind IN ('chat_summary','emergency') AND ts >= datetime('now','-1 day')", one=True)["n"]
    return n < cap


def _store_lead(source, phone, text, payload):
    ex("INSERT INTO calls(from_number,transcript,payload) VALUES(?,?,?)", (phone[:40], text[:8000], json.dumps({"source": source, **payload})[:4000]))


@bp.route("/api/chat/riepilogo", methods=["POST"])
def api_chat_summary():
    """Riepilogo della conversazione -> WhatsApp al team di turno. Senza Twilio: registra la richiesta e restituisce il link wa.me."""
    check_csrf()
    d = request.get_json(silent=True) or {}
    if d.get("website"):                      # honeypot
        return jsonify(ok=True)
    ip = request.remote_addr or "?"
    if not notify.rate_ok(f"sum:{ip}", 3, 600):
        return jsonify(error="Troppe richieste: riprova tra qualche minuto."), 429
    name, phone = _clean(d.get("name"), 80), _clean(d.get("phone"), 30)
    if not _valid_phone(phone):
        return jsonify(error="Inserisci un numero di telefono valido."), 400
    if not d.get("consent"):
        return jsonify(error="Serve il consenso a essere ricontattato."), 400
    msgs = [{"role": "assistant" if m.get("role") == "assistant" else "user", "content": _clean(m.get("content"), 500)}
            for m in (d.get("messages") or [])[-20:] if m.get("content")]
    text = _chat_summary(msgs, name, phone)
    _store_lead("chat", phone, text, {"name": name})
    metrics.track("chat_summary", metrics.visitor_hash(request))
    res = dict(configured=notify.twilio_ready(), sent=0)
    if res["configured"] and _wa_cap_ok():
        res = notify.notify_duty(text, "chat_summary")
    to = notify.normalize_number(get_setting("whatsapp", "")) or notify.normalize_number(_emergency_cfg()[1])
    link = f"https://wa.me/{to.lstrip('+')}?text=" + urllib.parse.quote(text) if to else ""
    return jsonify(ok=True, configured=res["configured"], sent=res.get("sent", 0), wa_link=link)


@bp.route("/api/emergenza", methods=["POST"])
def api_emergency():
    """Richiesta di richiamo urgente: avviso immediato su WhatsApp a chi è di turno."""
    check_csrf()
    d = request.get_json(silent=True) or {}
    if d.get("website"):
        return jsonify(ok=True)
    if not notify.rate_ok(f"em:{request.remote_addr or '?'}", 5, 600):
        return jsonify(error="Hai già inviato più richieste: chiama direttamente il numero indicato."), 429
    name, phone, note = _clean(d.get("name"), 80), _clean(d.get("phone"), 30), _clean(d.get("note"), 400)
    if not _valid_phone(phone):
        return jsonify(error="Inserisci un numero di telefono valido per essere richiamato."), 400
    text = f"🚨 EMERGENZA 24h – richiesta di richiamo\nNome: {name or 'non indicato'}\nTelefono: {phone}\nOra: {metrics.now_local():%d/%m/%Y %H:%M}\nProblema: {note or 'non indicato'}"
    _store_lead("emergenza", phone, text, {"name": name})
    metrics.track("emergency", metrics.visitor_hash(request))
    res = dict(configured=notify.twilio_ready(), sent=0)
    if res["configured"] and _wa_cap_ok():
        res = notify.notify_duty(text, "emergency")
    return jsonify(ok=True, configured=res["configured"], sent=res.get("sent", 0))


@bp.route("/webhook/vapi", methods=["POST"])
def webhook_vapi():
    """Server URL di Vapi: a fine chiamata registra il riepilogo e lo gira su WhatsApp. Richiede il secret (Admin › Impostazioni)."""
    secret = notify.cfg("vapi_webhook_secret")
    got = request.headers.get("X-Vapi-Secret") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not secret or not got or not secrets.compare_digest(got, secret):
        abort(404)
    d = request.get_json(silent=True) or {}
    msg = d.get("message") if isinstance(d.get("message"), dict) else d
    if msg.get("type") != "end-of-call-report":
        return jsonify(ok=True)
    call = msg.get("call") or {}
    num = ((call.get("customer") or {}).get("number") or "")[:40]
    summary = (msg.get("summary") or (msg.get("analysis") or {}).get("summary") or "").strip()
    transcript = (msg.get("transcript") or "").strip()
    emerg = bool(notify.cfg("vapi_emergency_assistant_id")) and call.get("assistantId") == notify.cfg("vapi_emergency_assistant_id")
    text = (("🚨 EMERGENZA – " if emerg else "📞 ") + "Chiamata all'assistente vocale\n" + f"Da: {num or 'sito (web)'}\n"
            f"Ora: {metrics.now_local():%d/%m/%Y %H:%M}\nRiepilogo: {(summary or transcript or 'nessun contenuto')[:700]}")
    ex("INSERT INTO calls(from_number,transcript,payload) VALUES(?,?,?)",
       (num, (transcript or summary)[:8000], json.dumps({"source": "vapi", "id": call.get("id"), "ended": msg.get("endedReason"), "emergency": emerg})[:2000]))
    metrics.track("vapi_call", call.get("id") or "")
    if notify.twilio_ready() and _wa_cap_ok():
        notify.fire(text, "emergency" if emerg else "vapi_call")
    return jsonify(ok=True)


@bp.route("/api/tariffe")
def api_tariffe():
    """Stima indicativa per il configuratore: solo se il titolare l'ha attivata e solo voci marcate «sul sito» con un prezzo > 0 (nessun segreto)."""
    out = {}
    if get_setting("tariffe_pubbliche", "0") == "1":
        for t in q("SELECT service, MIN(price) p FROM tariffe WHERE active=1 AND public=1 AND price>0 AND service!='' AND unit!='al mq' GROUP BY service"):
            out[t["service"]] = round(t["p"])
    r = jsonify(enabled=bool(out), prices=out)
    r.headers["Cache-Control"] = "no-store"
    return r


@bp.route("/api/csrf")
def api_csrf():
    """Token fresco: serve alle pagine rimaste aperte o in cache oltre la durata della sessione."""
    r = jsonify(token=csrf_token())
    r.headers["Cache-Control"] = "no-store"
    return r


@bp.route("/api/chat", methods=["POST"])
def api_chat():
    check_csrf()
    d = request.get_json(silent=True) or {}
    msgs = [{"role": "assistant" if m.get("role") == "assistant" else "user", "content": _clean(m.get("content"), 500)}
            for m in (d.get("messages") or [])[-10:] if m.get("content")]
    if not msgs:
        return jsonify(error="vuoto"), 400
    try:
        metrics.track("chat_msg", metrics.visitor_hash(request))
    except Exception:
        pass
    text, action = ai.chat(msgs)
    return jsonify(reply=text, action=action)


@bp.route("/privacy")
def privacy():
    s = dict(ctx())
    # i segnaposto "[DA COMPLETARE ...]" non devono mai comparire al pubblico: si completano da Admin > Testi
    s["privacy"] = re.sub(r"\s*\[DA COMPLETARE[^\]]*\]", "", s.get("privacy", "") or "")
    return render_template("privacy.html", s=s, demo=(os.getenv("APP_MODE", "demo") == "demo"))


@bp.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nDisallow: /admin\nSitemap: {request.host_url}sitemap.xml\n", mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap():
    base = request.host_url.rstrip("/")
    xml = ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f'<url><loc>{base}/</loc></url><url><loc>{base}/privacy</loc></url></urlset>')
    return Response(xml, mimetype="application/xml")


@bp.route("/manifest.webmanifest")
def manifest():
    return jsonify({
        "name": "La Music Company Service", "short_name": "LMC Service", "lang": "it",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#ffffff", "theme_color": "#0e1a30",
        "shortcuts": [
            {"name": "Richiedi un preventivo", "short_name": "Preventivo", "url": "/#preventivo", "icons": [{"src": "/static/img/icon-192.png", "sizes": "192x192"}]},
            {"name": "Emergenza 24h", "short_name": "Emergenza", "url": "/?sos=1", "icons": [{"src": "/static/img/icon-192.png", "sizes": "192x192"}]},
            {"name": "Prenota un appuntamento", "short_name": "Prenota", "url": "/#prenota", "icons": [{"src": "/static/img/icon-192.png", "sizes": "192x192"}]}],
        "icons": [{"src": "/static/img/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                  {"src": "/static/img/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]})


@bp.route("/sw.js")
def sw():
    r = send_from_directory(os.path.join(os.path.dirname(__file__), "..", "app", "static", "js"), "sw.js")
    r.headers["Service-Worker-Allowed"] = "/"
    r.headers["Cache-Control"] = "no-cache"
    return r
