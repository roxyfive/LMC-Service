import os
import json
import time
from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for, session, jsonify, abort,
                   flash, send_file)
from werkzeug.security import check_password_hash, generate_password_hash
from .db import q, ex, get_setting, set_setting, all_settings
from .security import admin_required, csrf_token, check_csrf, current_user
from . import rbac
from .config import CATEGORIES, MODE
from .media import save_upload, delete_files
from .mailer import send_mail

bp = Blueprint("admin", __name__, url_prefix="/admin")
_attempts = {}

MODULES = {
    "clienti": {"table": "clients", "title": "Clienti", "fields": [
        ("name", "Nome / ragione sociale", "text"), ("phone", "Telefono", "text"), ("email", "Email", "text"),
        ("address", "Indirizzo (per fattura)", "text"), ("piva", "Partita IVA", "text"), ("cf", "Codice fiscale", "text"),
        ("sdi_code", "Codice destinatario SDI", "text"), ("pec", "PEC", "text"), ("notes", "Note", "area")]},
    "fornitori": {"table": "suppliers", "title": "Fornitori", "fields": [
        ("name", "Nome", "text"), ("category", "Categoria", "text"), ("phone", "Telefono", "text"),
        ("email", "Email", "text"), ("notes", "Note", "area")]},
    "magazzino": {"table": "equipment", "title": "Magazzino attrezzature", "fields": [
        ("name", "Attrezzatura", "text"), ("category", "Categoria (audio/luci/video)", "text"),
        ("qty", "Quantità", "number"), ("status", "Stato", "select:disponibile,in uso,in riparazione,fuori servizio"),
        ("notes", "Note", "area")]},
    "eventi": {"table": "events", "title": "Calendario eventi", "fields": [
        ("title", "Titolo", "text"), ("date", "Data", "date"), ("place", "Luogo", "text"),
        ("event_type", "Tipo di evento", "select:Matrimonio,Festa privata,Evento aziendale / Meeting,Concerto / Show,Discoteca / Locale,Altro"),
        ("status", "Stato", "select:confermato,svolto,annullato"), ("client_id", "Cliente", "client"), ("notes", "Note", "area")]},
    "prima-nota": {"table": "journal", "title": "Prima nota", "fields": [
        ("date", "Data", "date"), ("description", "Descrizione", "text"), ("type", "Tipo", "select:entrata,uscita"),
        ("amount", "Importo €", "number"), ("notes", "Note", "area")]},
    "team": {"table": "team", "title": "Team e Contatti", "order": "sort, id", "fields": [
        ("name", "Nome", "text"), ("role", "Ruolo", "text"), ("phone", "Telefono / WhatsApp", "text"), ("email", "Email", "text"),
        ("note", "Nota (es. orari, disponibilità)", "area"), ("visible", "Mostra sul sito e all'assistente", "select:si,no"),
        ("sort", "Ordine (0 = primo)", "number"),
        ("notify", "Riceve notifiche e report su WhatsApp", "select:si,no"), ("on_duty", "Di turno (riceve riepiloghi ed emergenze)", "select:si,no")]},
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
            un = request.form.get("username", "").strip()
            u = q("SELECT * FROM admin_users WHERE lower(username)=lower(?)", (un,), one=True)
            if u and check_password_hash(u["pw_hash"], request.form.get("password", "")):
                if not u["active"]:
                    rbac.audit("Accesso rifiutato (utente disattivato)", un, user=u)
                    err = "Questo utente è stato disattivato. Contatta il titolare."
                else:
                    session.clear()
                    session["uid"] = u["id"]
                    session["admin"] = u["username"]
                    ex("UPDATE admin_users SET last_login=datetime('now') WHERE id=?", (u["id"],))
                    rbac.audit("Accesso", "", user=u)
                    return redirect(url_for("admin.dashboard"))
            else:
                _attempts[ip].append(now)
                rbac.audit("Accesso fallito", un[:40])
                err = "Credenziali errate."
    return render_template("admin/login.html", err=err, csrf=csrf_token())


@bp.route("/logout", methods=["POST"])
@admin_required
def logout():
    rbac.audit("Uscita")
    session.clear()
    return redirect(url_for("pub.index"))


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
    from .admin_gest import set_appointment_status
    set_appointment_status(i, st)
    return redirect(request.referrer or url_for("admin.richieste"))


@bp.route("/preventivo/<int:i>/stato", methods=["POST"])
@admin_required
def quote_stato(i):
    st = request.form.get("stato")
    if st not in ("nuova", "in lavorazione", "inviata", "confermata", "chiusa"):
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


# ---------- foto e video (galleria eventi) ----------
@bp.route("/foto")
@admin_required
def foto():
    flt = request.args.get("v", "")
    sql = "SELECT * FROM media WHERE placeholder=0"
    if flt == "bozze":
        sql += " AND hidden=1"
    elif flt == "pubblicate":
        sql += " AND hidden=0"
    items = q(sql + " ORDER BY featured DESC, sort, id")
    cnt = dict(tutte=q("SELECT COUNT(*) c FROM media WHERE placeholder=0", one=True)["c"], bozze=q("SELECT COUNT(*) c FROM media WHERE placeholder=0 AND hidden=1", one=True)["c"])
    cnt["pubblicate"] = cnt["tutte"] - cnt["bozze"]
    return render_template("admin/foto.html", items=items, cats=CATEGORIES, flt=flt, cnt=cnt,
                           events=q("SELECT id,title,date FROM events ORDER BY date DESC LIMIT 80"),
                           invoices=q("SELECT id,number,client_name FROM invoices WHERE number IS NOT NULL AND number!='' ORDER BY id DESC LIMIT 60"),
                           event_types=["Matrimonio", "Festa privata", "Evento aziendale / Meeting", "Concerto / Show", "Discoteca / Locale", "Altro"])


@bp.route("/foto/upload", methods=["POST"])
@admin_required
def foto_upload():
    """Caricamento con didascalia OBBLIGATORIA, tipo e data dell'evento. Le foto partono NASCOSTE: si pubblicano quando si vuole."""
    ok, errs = [], []
    f = request.form
    cat = f.get("category") if f.get("category") in CATEGORIES else "Eventi"
    caption = f.get("caption", "").strip()[:300]
    if not caption:
        msg = "Scrivi una didascalia: è obbligatoria (serve a chi guarda e a Google)."
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify(ok=[], errors=[msg])
        flash(msg)
        return redirect(url_for("admin.foto"))
    ev = int(f["event_id"]) if f.get("event_id", "").isdigit() else None
    inv = int(f["invoice_id"]) if f.get("invoice_id", "").isdigit() else None
    mx = q("SELECT COALESCE(MAX(sort),0) m FROM media", one=True)["m"]
    who = current_user()["username"]
    for fl in request.files.getlist("files"):
        if not fl.filename:
            continue
        try:
            base, kind = save_upload(fl)
            mx += 1
            ex("""INSERT INTO media(filename,kind,title,caption,category,sort,source,hidden,event_type,event_date,event_id,invoice_id,uploaded_by)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (base, kind, (f.get("title", "").strip() or caption)[:60], caption, cat, mx, "caricata dall'admin", 1, f.get("event_type", "")[:60],
                f.get("event_date", "")[:10], ev, inv, who))
            ok.append(fl.filename)
        except ValueError as e:
            errs.append(f"{fl.filename}: {e}")
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=ok, errors=errs)
    for e in errs:
        flash(e)
    if ok:
        flash(f"{len(ok)} file caricati e NASCOSTI: controllali e premi «Pubblica» quando vuoi.")
    return redirect(url_for("admin.foto", v="bozze"))


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
    caption = f.get("caption", "").strip()[:300]
    if not caption:
        flash("La didascalia è obbligatoria.")
        return redirect(url_for("admin.foto") + f"#m{i}")
    ev = int(f["event_id"]) if f.get("event_id", "").isdigit() else None
    inv = int(f["invoice_id"]) if f.get("invoice_id", "").isdigit() else None
    if rbac.is_admin():
        if f.get("featured"):
            ex("UPDATE media SET featured=0")
        ex("""UPDATE media SET title=?,caption=?,category=?,show_home=?,show_gallery=?,show_intro=?,featured=?,hidden=?,event_type=?,event_date=?,event_id=?,invoice_id=?
              WHERE id=?""", (f.get("title", "")[:100], caption, cat, int(bool(f.get("show_home"))), int(bool(f.get("show_gallery"))),
                              int(bool(f.get("show_intro"))), int(bool(f.get("featured"))), int(bool(f.get("hidden"))), f.get("event_type", "")[:60],
                              f.get("event_date", "")[:10], ev, inv, i))
    else:      # il collaboratore corregge titolo, didascalia e dati dell'evento: pubblicare o togliere dal sito è del titolare
        ex("UPDATE media SET title=?,caption=?,category=?,event_type=?,event_date=?,event_id=? WHERE id=?",
           (f.get("title", "")[:100], caption, cat, f.get("event_type", "")[:60], f.get("event_date", "")[:10], ev, i))
    return redirect(url_for("admin.foto", v=request.args.get("v", "")) + f"#m{i}")


@bp.route("/foto/<int:i>/pubblica", methods=["POST"])
@admin_required
def foto_publish(i):
    r = q("SELECT hidden FROM media WHERE id=?", (i,), one=True) or abort(404)
    ex("UPDATE media SET hidden=? WHERE id=?", (0 if r["hidden"] else 1, i))
    flash("Pubblicata sul sito." if r["hidden"] else "Nascosta: non è più visibile sul sito.")
    return redirect(request.referrer or url_for("admin.foto"))


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
TEXT_FIELDS = [("brand", "Nome attività (completo)", "text"), ("brand_short", "Nome breve", "text"), ("owner", "Titolare (nome e cognome)", "text"),
               ("city", "Città", "text"), ("founded", "Data di fondazione (es. 16/02/2025)", "text"),
               ("claim", "Claim", "text"), ("tagline", "Sottotitolo", "text"), ("chi_siamo", "Chi siamo (storia)", "area"),
               ("zone", "Zone coperte", "text"), ("telefono", "Telefono", "text"), ("whatsapp", "WhatsApp (solo numeri, con prefisso 39)", "text"),
               ("email", "Email", "text"), ("indirizzo", "Indirizzo / città", "text"), ("orari", "Orari", "text"),
               ("instagram", "Instagram – URL del profilo", "text"), ("facebook", "Facebook – URL della pagina", "text"),
               ("facebook_nome", "Facebook – nome pagina mostrato nel footer", "text"), ("sito_url", "Sito ufficiale – URL (footer \"Seguici\")", "text"), ("tiktok", "TikTok – URL", "text"),
               ("chat_suggerimenti", "Suggerimenti chat – domande pronte, una per riga, max 4 (vuoto = automatiche dai dati del sito)", "area"),
               ("dati_societari", "Dati societari nel footer (ragione sociale, P.IVA, sede legale)", "text"),
               ("privacy", "Informativa privacy – testo principale", "area"),
               ("privacy_extra", "Informativa privacy – dettagli (fornitori, sede dei dati, conservazione, basi giuridiche)", "area")]


@bp.route("/testi", methods=["GET", "POST"])
@admin_required
def testi():
    if request.method == "POST":
        for k, _l, _t in TEXT_FIELDS:
            if k in request.form:        # un campo assente dal modulo non viene azzerato
                set_setting(k, request.form.get(k, "")[:3000])
        names, texts = request.form.getlist("sv_nome"), request.form.getlist("sv_testo")
        set_setting("servizi", json.dumps([{"nome": n[:60], "testo": t[:300]} for n, t in zip(names, texts) if n.strip()],
                                          ensure_ascii=False))
        set_setting("intro_righe", json.dumps([x.strip()[:140] for x in request.form.get("intro_righe", "").splitlines() if x.strip()],
                                              ensure_ascii=False))
        set_setting("stats", json.dumps(_parse_stats(request.form.get("stats_righe", "")), ensure_ascii=False))
        flash("Testi salvati")
        return redirect(url_for("admin.testi"))
    s = all_settings()
    serv = json.loads(s.get("servizi", "[]") or "[]")
    intro = "\n".join(json.loads(s.get("intro_righe", "[]") or "[]"))
    try:
        stats = "\n".join(f"{x['label']} | {x['value']} | {x.get('suffix', '')}" for x in json.loads(s.get("stats", "") or "[]"))
    except (ValueError, KeyError, TypeError):
        stats = ""
    return render_template("admin/testi.html", s=s, fields=TEXT_FIELDS, serv=serv, intro=intro, stats=stats)


def _parse_stats(txt):
    """Una cifra per riga: «Eventi realizzati | 150 | +» -> [{label, value, suffix}] (righe non valide ignorate, max 6)."""
    out = []
    for ln in txt.splitlines():
        parts = [x.strip() for x in ln.split("|")]
        if len(parts) >= 2 and parts[0] and parts[1].replace(".", "", 1).isdigit():
            out.append({"label": parts[0][:40], "value": int(float(parts[1])), "suffix": (parts[2] if len(parts) > 2 else "")[:6]})
    return out[:6]


@bp.route("/password", methods=["GET", "POST"])
@admin_required
def password():
    """Cambio password dell'utente collegato (obbligatorio al primo accesso con una password temporanea)."""
    msg, ok = "", False
    u = current_user()
    if request.method == "POST":
        check_csrf()
        old, new, new2 = request.form.get("old", ""), request.form.get("new", ""), request.form.get("new2", "")
        if not check_password_hash(u["pw_hash"], old):
            msg = "La password attuale non è corretta."
        elif len(new) < 10:
            msg = "La nuova password deve avere almeno 10 caratteri."
        elif new != new2:
            msg = "Le due nuove password non coincidono."
        elif new == old:
            msg = "Scegli una password diversa da quella attuale."
        else:
            ex("UPDATE admin_users SET pw_hash=?, must_change=0 WHERE id=?", (generate_password_hash(new), u["id"]))
            msg, ok = "Password cambiata. Alla prossima volta usa quella nuova.", True
    return render_template("admin/password.html", msg=msg, ok=ok, forced=bool(u["must_change"]) and not ok)


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


rbac.install(bp)
from . import admin_ext  # noqa: E402,F401  (registra Impostazioni e Report sullo stesso blueprint)
from . import admin_gest  # noqa: E402,F401  (dashboard, agenda, fatture, acconti, tariffe, statistiche, utenti...)
from . import reviews  # noqa: E402,F401  (recensioni: pagine admin e pagina pubblica)
