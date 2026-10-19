import os
import json
import time
from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for, session, jsonify, abort,
                   flash, send_file)
from werkzeug.security import check_password_hash
from .db import q, ex, get_setting, set_setting, all_settings
from .security import admin_required, csrf_token, check_csrf
from .config import CATEGORIES, MODE
from .media import save_upload, delete_files
from .mailer import send_mail
from .pdfgen import document_pdf

bp = Blueprint("admin", __name__, url_prefix="/admin")
_attempts = {}

MODULES = {
    "clienti": {"table": "clients", "title": "Clienti", "fields": [
        ("name", "Nome", "text"), ("phone", "Telefono", "text"), ("email", "Email", "text"), ("notes", "Note", "area")]},
    "fornitori": {"table": "suppliers", "title": "Fornitori", "fields": [
        ("name", "Nome", "text"), ("category", "Categoria", "text"), ("phone", "Telefono", "text"),
        ("email", "Email", "text"), ("notes", "Note", "area")]},
    "magazzino": {"table": "equipment", "title": "Magazzino attrezzature", "fields": [
        ("name", "Attrezzatura", "text"), ("category", "Categoria (audio/luci/video)", "text"),
        ("qty", "Quantità", "number"), ("status", "Stato", "select:disponibile,in uso,in riparazione,fuori servizio"),
        ("notes", "Note", "area")]},
    "eventi": {"table": "events", "title": "Calendario eventi", "fields": [
        ("title", "Titolo", "text"), ("date", "Data", "date"), ("place", "Luogo", "text"),
        ("client_id", "Cliente", "client"), ("notes", "Note", "area")]},
    "prima-nota": {"table": "journal", "title": "Prima nota", "fields": [
        ("date", "Data", "date"), ("description", "Descrizione", "text"), ("type", "Tipo", "select:entrata,uscita"),
        ("amount", "Importo €", "number"), ("notes", "Note", "area")]},
    "team": {"table": "team", "title": "Team e Contatti", "order": "sort, id", "fields": [
        ("name", "Nome", "text"), ("role", "Ruolo", "text"), ("phone", "Telefono / WhatsApp", "text"), ("email", "Email", "text"),
        ("note", "Nota (es. orari, disponibilità)", "area"), ("visible", "Mostra sul sito e all'assistente", "select:si,no"),
        ("sort", "Ordine (0 = primo)", "number"),
        ("notify", "Riceve notifiche e report su WhatsApp", "select:si,no"), ("on_duty", "Di turno (riceve riepiloghi ed emergenze)", "select:si,no")]},
    "recensioni": {"table": "reviews", "title": "Dicono di noi", "fields": [
        ("author", "Autore", "text"), ("text", "Testo (solo recensioni reali)", "area"), ("source", "Fonte", "text")]},
}


@bp.context_processor
def inject():
    return {"csrf": csrf_token(), "modules": MODULES, "mode": MODE}


@bp.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        check_csrf()
        ip = request.remote_addr
        now = time.time()
        _attempts[ip] = [t for t in _attempts.get(ip, []) if now - t < 300]
        if len(_attempts[ip]) >= 5:
            err = "Troppi tentativi. Riprova tra 5 minuti."
        else:
            u = q("SELECT * FROM admin_users WHERE username=?", (request.form.get("username", ""),), one=True)
            if u and check_password_hash(u["pw_hash"], request.form.get("password", "")):
                session.clear()
                session["admin"] = u["username"]
                return redirect(url_for("admin.dashboard"))
            _attempts[ip].append(now)
            err = "Credenziali errate."
    return render_template("admin/login.html", err=err, csrf=csrf_token())


@bp.route("/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    return redirect(url_for("pub.index"))


@bp.route("/")
@admin_required
def dashboard():
    today = date.today().isoformat()
    agenda = q("SELECT * FROM appointments WHERE slot_date>=? AND status!='annullato' ORDER BY slot_date,slot_time", (today,))
    new_q = q("SELECT COUNT(*) c FROM quotes WHERE status='nuova'", one=True)["c"]
    pend = q("SELECT COUNT(*) c FROM appointments WHERE status='in attesa'", one=True)["c"]
    evs = q("SELECT * FROM events WHERE date>=? ORDER BY date LIMIT 8", (today,))
    return render_template("admin/dashboard.html", agenda=agenda, new_q=new_q, pend=pend, evs=evs)


# ---------- richieste ----------
@bp.route("/richieste")
@admin_required
def richieste():
    return render_template("admin/richieste.html",
                           apps=q("SELECT * FROM appointments ORDER BY created DESC"),
                           quotes=q("SELECT * FROM quotes ORDER BY created DESC"))


@bp.route("/appuntamento/<int:i>/stato", methods=["POST"])
@admin_required
def app_stato(i):
    st = request.form.get("stato")
    if st not in ("in attesa", "confermato", "annullato", "completato"):
        abort(400)
    ex("UPDATE appointments SET status=? WHERE id=?", (st, i))
    a = q("SELECT * FROM appointments WHERE id=?", (i,), one=True)
    if a and st in ("confermato", "annullato"):
        send_mail(a["email"], f"Appuntamento {st} – LMC Service",
                  f"Ciao {a['name']}, il tuo appuntamento del {a['slot_date']} alle {a['slot_time']} è {st}.\nLMC Service")
    return redirect(request.referrer or url_for("admin.richieste"))


@bp.route("/preventivo/<int:i>/stato", methods=["POST"])
@admin_required
def quote_stato(i):
    st = request.form.get("stato")
    if st not in ("nuova", "in lavorazione", "inviata", "chiusa"):
        abort(400)
    ex("UPDATE quotes SET status=? WHERE id=?", (st, i))
    return redirect(url_for("admin.richieste"))


@bp.route("/preventivo/<int:i>/cliente", methods=["POST"])
@admin_required
def quote_to_client(i):
    r = q("SELECT * FROM quotes WHERE id=?", (i,), one=True)
    if r:
        ex("INSERT INTO clients(name,phone,email,notes) VALUES(?,?,?,?)",
           (r["name"], r["phone"], r["email"], f"Da preventivo: {r['event_type']} {r['event_date']} {r['place']}"))
    flash("Cliente creato")
    return redirect(url_for("admin.richieste"))


# ---------- disponibilità ----------
@bp.route("/disponibilita", methods=["GET", "POST"])
@admin_required
def disponibilita():
    if request.method == "POST":
        act = request.form.get("act")
        if act == "add":
            ex("INSERT INTO availability(weekday,start,end) VALUES(?,?,?)",
               (int(request.form["weekday"]), request.form["start"], request.form["end"]))
        elif act == "del":
            ex("DELETE FROM availability WHERE id=?", (int(request.form["id"]),))
        elif act == "close":
            ex("INSERT INTO closures(date,note) VALUES(?,?)", (request.form["date"], request.form.get("note", "")))
        elif act == "open":
            ex("DELETE FROM closures WHERE id=?", (int(request.form["id"]),))
        elif act == "slot":
            set_setting("slot_minutes", str(max(15, min(240, int(request.form["slot_minutes"])))))
        return redirect(url_for("admin.disponibilita"))
    return render_template("admin/disponibilita.html",
                           av=q("SELECT * FROM availability ORDER BY weekday,start"),
                           cl=q("SELECT * FROM closures ORDER BY date"),
                           slot=get_setting("slot_minutes", "60"),
                           days=["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"])


# ---------- foto e video ----------
@bp.route("/foto")
@admin_required
def foto():
    return render_template("admin/foto.html", items=q("SELECT * FROM media ORDER BY featured DESC, sort, id"), cats=CATEGORIES)


@bp.route("/foto/upload", methods=["POST"])
@admin_required
def foto_upload():
    ok, errs = [], []
    cat = request.form.get("category") if request.form.get("category") in CATEGORIES else "Eventi"
    mx = q("SELECT COALESCE(MAX(sort),0) m FROM media", one=True)["m"]
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        try:
            base, kind = save_upload(f)
            mx += 1
            ex("INSERT INTO media(filename,kind,title,category,sort,source) VALUES(?,?,?,?,?,?)",
               (base, kind, os.path.splitext(f.filename)[0][:60], cat, mx, "caricata dall'admin"))
            ok.append(f.filename)
        except ValueError as e:
            errs.append(f"{f.filename}: {e}")
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=ok, errors=errs)
    for e in errs:
        flash(e)
    return redirect(url_for("admin.foto"))


@bp.route("/foto/sincronizza", methods=["POST"])
@admin_required
def foto_sync():
    from .foto_sync import sync
    done, skipped = sync()
    flash(f"Cartella foto/organizzate: {len(done)} file importati, {len(skipped)} saltati." + (" " + "; ".join(skipped[:5]) if skipped else ""))
    return redirect(url_for("admin.foto"))


@bp.route("/foto/<int:i>", methods=["POST"])
@admin_required
def foto_update(i):
    f = request.form
    cat = f.get("category") if f.get("category") in CATEGORIES else "Eventi"
    if f.get("featured"):
        ex("UPDATE media SET featured=0")
    ex("""UPDATE media SET title=?,caption=?,category=?,show_home=?,show_gallery=?,show_intro=?,featured=?,hidden=?
          WHERE id=?""", (f.get("title", "")[:100], f.get("caption", "")[:300], cat, int(bool(f.get("show_home"))),
                          int(bool(f.get("show_gallery"))), int(bool(f.get("show_intro"))),
                          int(bool(f.get("featured"))), int(bool(f.get("hidden"))), i))
    return redirect(url_for("admin.foto") + f"#m{i}")


@bp.route("/foto/<int:i>/elimina", methods=["POST"])
@admin_required
def foto_delete(i):
    r = q("SELECT filename FROM media WHERE id=?", (i,), one=True)
    if r:
        delete_files(r["filename"])
        ex("DELETE FROM media WHERE id=?", (i,))
    return redirect(url_for("admin.foto"))


@bp.route("/foto/riordina", methods=["POST"])
@admin_required
def foto_reorder():
    ids = (request.get_json(silent=True) or {}).get("ids", [])
    for n, i in enumerate(ids):
        ex("UPDATE media SET sort=? WHERE id=?", (n, int(i)))
    return jsonify(ok=True)


# ---------- testi ----------
TEXT_FIELDS = [("claim", "Claim", "text"), ("tagline", "Sottotitolo", "text"), ("chi_siamo", "Chi siamo (storia)", "area"),
               ("zone", "Zone coperte", "text"), ("telefono", "Telefono", "text"), ("whatsapp", "WhatsApp (solo numeri, con prefisso 39)", "text"),
               ("email", "Email", "text"), ("indirizzo", "Indirizzo / città", "text"), ("orari", "Orari", "text"),
               ("instagram", "Instagram – URL del profilo", "text"), ("facebook", "Facebook – URL della pagina", "text"),
               ("facebook_nome", "Facebook – nome pagina mostrato nel footer", "text"), ("sito_url", "Sito ufficiale – URL (footer \"Seguici\")", "text"), ("tiktok", "TikTok – URL", "text"),
               ("threads", "Threads", "text"), ("x", "X", "text"), ("linktree", "Linktree", "text"),
               ("privacy", "Informativa privacy", "area")]


@bp.route("/testi", methods=["GET", "POST"])
@admin_required
def testi():
    if request.method == "POST":
        for k, _l, _t in TEXT_FIELDS:
            set_setting(k, request.form.get(k, "")[:3000])
        names, texts = request.form.getlist("sv_nome"), request.form.getlist("sv_testo")
        set_setting("servizi", json.dumps([{"nome": n[:60], "testo": t[:300]} for n, t in zip(names, texts) if n.strip()],
                                          ensure_ascii=False))
        set_setting("intro_righe", json.dumps([x.strip()[:140] for x in request.form.get("intro_righe", "").splitlines() if x.strip()],
                                              ensure_ascii=False))
        flash("Testi salvati")
        return redirect(url_for("admin.testi"))
    s = all_settings()
    serv = json.loads(s.get("servizi", "[]") or "[]")
    intro = "\n".join(json.loads(s.get("intro_righe", "[]") or "[]"))
    return render_template("admin/testi.html", s=s, fields=TEXT_FIELDS, serv=serv, intro=intro)


# ---------- gestionale generico ----------
def _cfg(mod):
    c = MODULES.get(mod)
    if not c:
        abort(404)
    return c


@bp.route("/m/<mod>", methods=["GET", "POST"])
@admin_required
def mod_list(mod):
    c = _cfg(mod)
    cols = [f[0] for f in c["fields"]]
    if request.method == "POST":
        ex(f"INSERT INTO {c['table']}({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
           tuple(request.form.get(k, "")[:2000] for k in cols))
        return redirect(url_for("admin.mod_list", mod=mod))
    rows = q(f"SELECT * FROM {c['table']} ORDER BY {c.get('order', 'id DESC')}")
    clients = q("SELECT id,name FROM clients ORDER BY name")
    extra = {}
    if mod == "prima-nota":
        extra["entrate"] = sum(r["amount"] or 0 for r in rows if r["type"] == "entrata")
        extra["uscite"] = sum(r["amount"] or 0 for r in rows if r["type"] == "uscita")
    return render_template("admin/modulo.html", mod=mod, c=c, rows=rows, clients=clients, extra=extra, row=None)


@bp.route("/m/<mod>/<int:i>", methods=["GET", "POST"])
@admin_required
def mod_edit(mod, i):
    c = _cfg(mod)
    cols = [f[0] for f in c["fields"]]
    if request.method == "POST":
        ex(f"UPDATE {c['table']} SET {','.join(k + '=?' for k in cols)} WHERE id=?",
           tuple(request.form.get(k, "")[:2000] for k in cols) + (i,))
        return redirect(url_for("admin.mod_list", mod=mod))
    row = q(f"SELECT * FROM {c['table']} WHERE id=?", (i,), one=True) or abort(404)
    clients = q("SELECT id,name FROM clients ORDER BY name")
    eq = assigned = None
    if mod == "eventi":
        eq = q("SELECT * FROM equipment ORDER BY name")
        assigned = q("""SELECT ee.id,ee.qty,e.name FROM event_equipment ee JOIN equipment e ON e.id=ee.equipment_id
                        WHERE ee.event_id=?""", (i,))
    return render_template("admin/modulo.html", mod=mod, c=c, rows=[], clients=clients, extra={}, row=row,
                           eq=eq, assigned=assigned)


@bp.route("/m/<mod>/<int:i>/elimina", methods=["POST"])
@admin_required
def mod_del(mod, i):
    c = _cfg(mod)
    ex(f"DELETE FROM {c['table']} WHERE id=?", (i,))
    return redirect(url_for("admin.mod_list", mod=mod))


@bp.route("/eventi/<int:i>/attrezzatura", methods=["POST"])
@admin_required
def event_equipment(i):
    if request.form.get("del"):
        ex("DELETE FROM event_equipment WHERE id=?", (int(request.form["del"]),))
    else:
        ex("INSERT INTO event_equipment(event_id,equipment_id,qty) VALUES(?,?,?)",
           (i, int(request.form["equipment_id"]), max(1, int(request.form.get("qty", 1)))))
    return redirect(url_for("admin.mod_edit", mod="eventi", i=i))


# ---------- documenti (preventivi / fatture) ----------
def _parse_items(txt):
    items = []
    for ln in txt.splitlines():
        p = [x.strip() for x in ln.split(";")]
        if len(p) >= 3 and p[0]:
            try:
                items.append({"desc": p[0][:120], "qty": float(p[1].replace(",", ".")), "price": float(p[2].replace(",", "."))})
            except ValueError:
                continue
    return items


@bp.route("/documenti", methods=["GET", "POST"])
@admin_required
def documenti():
    if request.method == "POST":
        items = _parse_items(request.form.get("items", ""))
        total = round(sum(x["qty"] * x["price"] for x in items), 2)
        kind = "fattura" if request.form.get("kind") == "fattura" else "preventivo"
        n = q("SELECT COUNT(*) c FROM documents WHERE kind=?", (kind,), one=True)["c"] + 1
        num = f"{'F' if kind == 'fattura' else 'P'}{date.today().year}-{n:03d}"
        ex("INSERT INTO documents(kind,number,client_id,date,items,total,notes) VALUES(?,?,?,?,?,?,?)",
           (kind, num, request.form.get("client_id") or None, date.today().isoformat(),
            json.dumps(items, ensure_ascii=False), total, request.form.get("notes", "")[:500]))
        return redirect(url_for("admin.documenti"))
    docs = q("""SELECT d.*,c.name client FROM documents d LEFT JOIN clients c ON c.id=d.client_id ORDER BY d.id DESC""")
    return render_template("admin/documenti.html", docs=docs, clients=q("SELECT id,name FROM clients ORDER BY name"))


@bp.route("/documenti/<int:i>.pdf")
@admin_required
def documento_pdf(i):
    d = q("SELECT * FROM documents WHERE id=?", (i,), one=True) or abort(404)
    cl = q("SELECT * FROM clients WHERE id=?", (d["client_id"],), one=True) if d["client_id"] else None
    path = document_pdf(d, cl, all_settings())
    return send_file(path, mimetype="application/pdf", download_name=f"{d['number']}.pdf")


@bp.route("/documenti/<int:i>/stato", methods=["POST"])
@admin_required
def documento_stato(i):
    st = request.form.get("stato")
    if st in ("bozza", "inviato", "pagato", "annullato"):
        ex("UPDATE documents SET status=? WHERE id=?", (st, i))
    return redirect(url_for("admin.documenti"))


@bp.route("/documenti/<int:i>/elimina", methods=["POST"])
@admin_required
def documento_del(i):
    ex("DELETE FROM documents WHERE id=?", (i,))
    return redirect(url_for("admin.documenti"))


# ---------- telefono (predisposto) ----------
@bp.route("/chiamate")
@admin_required
def chiamate():
    rows = []
    for r in q("SELECT * FROM calls ORDER BY id DESC LIMIT 200"):
        try:
            src = json.loads(r["payload"] or "{}").get("source", "telefono")
        except ValueError:
            src = "telefono"
        rows.append(dict(created=r["created"], from_number=r["from_number"], transcript=r["transcript"], source=src))
    return render_template("admin/chiamate.html", rows=rows,
                           enabled=os.getenv("PHONE_AI_ENABLED") == "1")


from . import admin_ext  # noqa: E402,F401  (registra Impostazioni e Report sullo stesso blueprint)
