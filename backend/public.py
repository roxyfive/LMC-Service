import os
import re
import json
import secrets
from datetime import date, datetime, timedelta
from flask import (Blueprint, render_template, request, jsonify, send_from_directory, abort,
                   Response, url_for)
from .db import q, ex, get_setting, all_settings
from .config import UPLOADS, CATEGORIES
from .security import check_csrf, csrf_token
from .mailer import send_mail
from . import ai
from . import vetrina

bp = Blueprint("pub", __name__)
FILE_RE = re.compile(r"^[0-9a-f]{32}(_\d+)?\.(webp|mp4|webm)$")
EVENT_TYPES = ["Matrimonio", "Festa privata", "Evento aziendale / Meeting", "Concerto / Show", "Discoteca / Locale", "Altro"]
SERVICES = ["Audio", "Luci", "Video", "Progettazione"]


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
    media = q("SELECT * FROM media WHERE hidden=0 ORDER BY featured DESC, sort, id")
    gallery = [m for m in media if m["show_gallery"] and m["kind"] == "image"]
    home = [m for m in media if m["show_home"] and m["kind"] == "image"]
    intro = [m for m in media if m["show_intro"] and m["kind"] == "image"] or home[:6]
    videos = [m for m in media if m["kind"] == "video"]
    hero = next((m for m in media if m["featured"] and m["kind"] == "image"), None)
    reviews = q("SELECT * FROM reviews WHERE hidden=0 ORDER BY id DESC")
    s["team"] = q("SELECT * FROM team WHERE visible='si' ORDER BY sort, id")
    used = {m["category"] for m in gallery}
    v = vetrina.build(media)
    v["stats"] = vetrina.stats(s, os.getenv("APP_MODE", "demo") == "demo")
    return render_template("index.html", s=s, gallery=gallery, home=home, intro=intro, videos=videos, v=v,
                           hero=hero, reviews=reviews, cats=[c for c in CATEGORIES if c in used],
                           has_placeholder=any(m["placeholder"] for m in gallery), event_types=EVENT_TYPES,
                           services=SERVICES, demo=(os.getenv("APP_MODE", "demo") == "demo"))


@bp.route("/media/<name>")
def media_file(name):
    if not FILE_RE.match(name):
        abort(404)
    base = name.split(".")[0].split("_")[0]
    row = q("SELECT hidden FROM media WHERE filename=?", (base,), one=True)
    if not row:
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
    send_mail(os.getenv("OWNER_EMAIL"), f"Nuovo preventivo: {name}",
              f"{name} – {phone} – {email}\n{d.get('event_type')} il {d.get('event_date')} a {d.get('place')}, "
              f"{d.get('guests')} ospiti\nServizi: {services}\n{d.get('notes')}")
    return jsonify(ok=True)


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
    text, action = ai.chat(msgs)
    return jsonify(reply=text, action=action)


@bp.route("/privacy")
def privacy():
    return render_template("privacy.html", s=ctx())


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
        "background_color": "#0a0a0a", "theme_color": "#e10600",
        "icons": [{"src": "/static/img/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                  {"src": "/static/img/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]})


@bp.route("/sw.js")
def sw():
    r = send_from_directory(os.path.join(os.path.dirname(__file__), "..", "app", "static", "js"), "sw.js")
    r.headers["Service-Worker-Allowed"] = "/"
    r.headers["Cache-Control"] = "no-cache"
    return r
