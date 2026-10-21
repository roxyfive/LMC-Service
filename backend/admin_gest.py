"""Gestionale LMC: dashboard, agenda, preventivi, fatture, acconti, tariffe, statistiche, WhatsApp, recensioni (admin),
utenti e permessi, registro attività, stato backup. Registrato sullo stesso blueprint `admin` (vedi admin.py)."""
import calendar
import json
import os
import re
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import render_template, request, redirect, url_for, flash, session, send_file, abort, jsonify
from werkzeug.security import generate_password_hash

from . import billing, notify, rbac
from .admin import bp, MODULES
from .config import DATA
from .db import q, ex, get_setting, set_setting, all_settings
from .mailer import send_mail
from .rbac import audit
from .security import admin_required, current_user, check_csrf

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
SERVICES = ["Audio", "Luci", "Video", "Allestimenti", "Videosorveglianza", "Progettazione"]
EVENT_TYPES = ["Matrimonio", "Festa privata", "Evento aziendale / Meeting", "Concerto / Show", "Discoteca / Locale", "Altro"]


@bp.app_template_filter("eur")
def _eur(x):
    return billing.eur(x)


@bp.app_template_filter("dmy")
def _dmy(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d and len(d) >= 10 else (d or "")


@bp.context_processor
def _inject():
    u = current_user()
    role = rbac.role_of(u) if u else ""
    return {"user": u, "role": role, "is_admin": role == rbac.ADMIN, "menu": rbac.menu_for(role) if u else [],
            "role_label": rbac.ROLES.get(role, ""), "suggest": session.pop("suggest", None)}


def _today():
    return date.today().isoformat()


def _only_admin():
    if not rbac.is_admin():
        abort(403)


def _by():
    u = current_user()
    return u["username"] if u else ""


# ====================================================================== DASHBOARD
@bp.route("/")
@admin_required
def dashboard():
    today = _today()
    month = today[:7]
    adm = rbac.is_admin()
    apps_today = q("SELECT * FROM appointments WHERE slot_date=? AND status!='annullato' ORDER BY slot_time", (today,))
    new_quotes = q("SELECT * FROM quotes WHERE status='nuova' ORDER BY created DESC LIMIT 6")
    n_new_q = q("SELECT COUNT(*) c FROM quotes WHERE status='nuova'", one=True)["c"]
    pend = q("SELECT * FROM appointments WHERE status='in attesa' AND slot_date>=? ORDER BY slot_date, slot_time LIMIT 6", (today,))
    n_pend = q("SELECT COUNT(*) c FROM appointments WHERE status='in attesa' AND slot_date>=?", (today,), one=True)["c"]
    upcoming = q("""SELECT 'evento' kind, id, date, title label, place extra FROM events WHERE date>=? AND status!='annullato'
                    UNION ALL SELECT 'appuntamento', id, slot_date, name, event_type FROM appointments WHERE slot_date>=? AND slot_date<=? AND status='confermato'
                    ORDER BY date LIMIT 8""", (today, today, (date.today() + timedelta(days=30)).isoformat()))
    d = dict(mese_label=f"{MESI[date.today().month - 1]} {date.today().year}", apps_today=apps_today, new_quotes=new_quotes, n_new_q=n_new_q, pend=pend, n_pend=n_pend, upcoming=upcoming, month=month, today=today,
             draft_photos=q("SELECT COUNT(*) c FROM media WHERE hidden=1 AND placeholder=0", one=True)["c"])
    if adm:
        inc = q("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE substr(date,1,7)=?", (month,), one=True)["s"]
        inc_prev = q("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE substr(date,1,7)=?",
                     ((date.today().replace(day=1) - timedelta(days=1)).isoformat()[:7],), one=True)["s"]
        invs = [billing.invoice_view(r) for r in q("SELECT * FROM invoices WHERE status IN ('emessa','pagata')")]
        d.update(incassi_mese=inc, incassi_prev=inc_prev, da_incassare=round(sum(i["resid"] for i in invs if i["show"] in ("emessa", "parziale", "scaduta")), 2),
                 scadute=[i for i in invs if i["show"] == "scaduta"], bozze=q("SELECT COUNT(*) c FROM invoices WHERE status='bozza'", one=True)["c"],
                 recensioni_att=q("SELECT COUNT(*) c FROM reviews WHERE status='in attesa'", one=True)["c"],
                 acconti_aperti=_open_documents()[:5])
    return render_template("admin/dashboard.html", **d)


def _open_documents():
    """Preventivi accettati/inviati con acconto versato ma non saldati."""
    out = []
    for r in q("SELECT d.*, c.name client FROM documents d LEFT JOIN clients c ON c.id=d.client_id WHERE d.kind='preventivo' AND d.status IN ('inviato','accettato')"):
        paid = billing.paid_of("document", r["id"])
        if paid > 0 and paid + 0.005 < (r["total"] or 0):
            out.append(dict(r, paid=paid, resid=round(r["total"] - paid, 2)))
    return out


# ====================================================================== AGENDA
def set_appointment_status(i, st):
    """Stesso comportamento della pagina Richieste: aggiorna lo stato e avvisa il cliente via email."""
    ex("UPDATE appointments SET status=? WHERE id=?", (st, i))
    a = q("SELECT * FROM appointments WHERE id=?", (i,), one=True)
    if a and st in ("confermato", "annullato"):
        send_mail(a["email"], f"Appuntamento {st} – LMC Service",
                  f"Ciao {a['name']}, il tuo appuntamento del {a['slot_date']} alle {a['slot_time']} è {st}.\nLMC Service")
    if a and st == "confermato" and rbac.is_admin():       # FASE 3: suggerisce i passi successivi (fattura, acconto)
        session["suggest"] = {"kind": "appuntamento", "id": i, "name": a["name"], "when": f"{_dmy(a['slot_date'])} {a['slot_time']}"}
    return a


def _month_arg():
    m = request.args.get("m", "")
    try:
        y, mo = int(m[:4]), int(m[5:7])
        date(y, mo, 1)
    except (ValueError, IndexError):
        t = date.today()
        y, mo = t.year, t.month
    return y, mo


@bp.route("/agenda")
@admin_required
def agenda():
    y, mo = _month_arg()
    weeks = calendar.Calendar(0).monthdatescalendar(y, mo)
    first, last = weeks[0][0].isoformat(), weeks[-1][-1].isoformat()
    apps, evs, qts, clo = {}, {}, {}, {}
    for a in q("SELECT * FROM appointments WHERE slot_date BETWEEN ? AND ? AND status!='annullato'", (first, last)):
        apps.setdefault(a["slot_date"], []).append(a)
    for e in q("SELECT * FROM events WHERE date BETWEEN ? AND ? AND status!='annullato'", (first, last)):
        evs.setdefault(e["date"], []).append(e)
    for r in q("SELECT * FROM quotes WHERE event_date BETWEEN ? AND ? AND status NOT IN ('chiusa')", (first, last)):
        qts.setdefault(r["event_date"], []).append(r)
    for c in q("SELECT * FROM closures WHERE date BETWEEN ? AND ?", (first, last)):
        clo[c["date"]] = c
    notes = {n["date"]: n for n in q("SELECT * FROM day_notes WHERE date BETWEEN ? AND ? AND note!=''", (first, last))}
    wd = {r["weekday"] for r in q("SELECT DISTINCT weekday FROM availability")}
    today = _today()
    cells = []
    for wk in weeks:
        row = []
        for d in wk:
            s = d.isoformat()
            conf = [a for a in apps.get(s, []) if a["status"] in ("confermato", "completato")]
            pend = [a for a in apps.get(s, []) if a["status"] == "in attesa"]
            if s in clo:
                st = "chiuso"
            elif conf or evs.get(s):
                st = "impegnato"
            elif pend or qts.get(s):
                st = "attesa"
            elif d.weekday() in wd:
                st = "libero"
            else:
                st = "off"
            row.append(dict(date=s, day=d.day, in_month=d.month == mo, state=st, past=s < today, today=s == today,
                            n=len(apps.get(s, [])) + len(evs.get(s, [])), note=bool(notes.get(s))))
        cells.append(row)
    sel = request.args.get("d") or (today if today[:7] == f"{y}-{mo:02d}" else f"{y}-{mo:02d}-01")
    try:
        date.fromisoformat(sel)
    except ValueError:
        sel = today
    from .public import free_slots
    day = dict(date=sel, apps=q("SELECT * FROM appointments WHERE slot_date=? AND status!='annullato' ORDER BY slot_time", (sel,)),
               evs=q("SELECT e.*, c.name client FROM events e LEFT JOIN clients c ON c.id=e.client_id WHERE e.date=? AND e.status!='annullato'", (sel,)),
               quotes=q("SELECT * FROM quotes WHERE event_date=? AND status!='chiusa'", (sel,)), closure=q("SELECT * FROM closures WHERE date=?", (sel,), one=True),
               note=q("SELECT * FROM day_notes WHERE date=?", (sel,), one=True), free=free_slots(sel))
    prev_m = (date(y, mo, 1) - timedelta(days=1)).strftime("%Y-%m")
    next_m = (date(y, mo, 28) + timedelta(days=5)).strftime("%Y-%m")
    return render_template("admin/agenda.html", cells=cells, y=y, mo=mo, mese=MESI[mo - 1], prev_m=prev_m, next_m=next_m, day=day, giorni=GIORNI, sel=sel)


@bp.route("/agenda/azione", methods=["POST"])
@admin_required
def agenda_azione():
    f = request.form
    act, day = f.get("act", ""), f.get("date", "")
    try:
        date.fromisoformat(day)
    except ValueError:
        abort(400)
    if act in ("conferma", "annulla") and f.get("id", "").isdigit():
        set_appointment_status(int(f["id"]), "confermato" if act == "conferma" else "annullato")
    elif act == "blocca":
        if not q("SELECT 1 FROM closures WHERE date=?", (day,), one=True):
            ex("INSERT INTO closures(date,note) VALUES(?,?)", (day, f.get("note", "")[:120]))
    elif act == "sblocca":
        ex("DELETE FROM closures WHERE date=?", (day,))
    return redirect(url_for("admin.agenda", m=day[:7], d=day))


@bp.route("/agenda/nota", methods=["POST"])
@admin_required
def agenda_nota():
    day = request.form.get("date", "")
    try:
        date.fromisoformat(day)
    except ValueError:
        abort(400)
    ex("INSERT INTO day_notes(date,note,user,updated) VALUES(?,?,?,datetime('now')) ON CONFLICT(date) DO UPDATE SET note=excluded.note,user=excluded.user,updated=excluded.updated",
       (day, request.form.get("note", "")[:600], _by()))
    return redirect(url_for("admin.agenda", m=day[:7], d=day))


# ====================================================================== PREVENTIVI (documenti) E RICHIESTE → PREVENTIVO
DOC_STATI = ["bozza", "inviato", "accettato", "rifiutato"]


@bp.route("/documenti", methods=["GET", "POST"])
@admin_required
def documenti():
    if request.method == "POST":
        items = billing.parse_items(request.form.getlist("desc"), request.form.getlist("qty"), request.form.getlist("price"))
        total = round(sum(x["qty"] * x["price"] for x in items), 2)
        did = ex("INSERT INTO documents(kind,number,client_id,date,items,total,notes) VALUES(?,?,?,?,?,?,?)",
                 ("preventivo", billing.prev_number(), request.form.get("client_id") or None, _today(), json.dumps(items, ensure_ascii=False),
                  total, request.form.get("notes", "")[:500]))
        flash("Preventivo creato.")
        return redirect(url_for("admin.documenti") + f"#d{did}")
    docs = []
    for d in q("SELECT d.*,c.name client FROM documents d LEFT JOIN clients c ON c.id=d.client_id WHERE d.kind='preventivo' ORDER BY d.id DESC"):
        paid = billing.paid_of("document", d["id"])
        docs.append(dict(d, paid=paid, resid=round((d["total"] or 0) - paid, 2),
                         acc="saldato" if (d["total"] or 0) > 0 and paid + 0.005 >= d["total"] else ("parziale" if paid > 0 else "nessun acconto"),
                         invoiced=q("SELECT number FROM invoices WHERE source_type='doc' AND source_id=?", (d["id"],), one=True)))
    return render_template("admin/documenti.html", docs=docs, clients=q("SELECT id,name FROM clients ORDER BY name"), stati=DOC_STATI,
                           tariffe=q("SELECT * FROM tariffe WHERE active=1 ORDER BY category,name"),
                           prefill=_quote_prefill(request.args.get("richiesta")))


def _quote_prefill(qid):
    """Righe suggerite per un preventivo nato da una richiesta del sito: una per servizio scelto, col prezzo della tariffa collegata."""
    if not (qid or "").isdigit():
        return None
    r = q("SELECT * FROM quotes WHERE id=?", (int(qid),), one=True)
    if not r:
        return None
    lines = []
    for sv in [x.strip() for x in (r["services"] or "").split(",") if x.strip()]:
        t = q("SELECT * FROM tariffe WHERE active=1 AND service=? ORDER BY price LIMIT 1", (sv,), one=True)
        lines.append(dict(desc=(t["name"] if t else sv) + (f" – {r['event_type']}" if r["event_type"] else ""), qty=1, price=t["price"] if t else 0))
    return dict(quote=r, lines=lines or [dict(desc="", qty=1, price=0)], client_id=billing.client_for(r["name"], r["phone"], r["email"]))


@bp.route("/documenti/<int:i>.pdf")
@admin_required
def documento_pdf(i):
    d = q("SELECT * FROM documents WHERE id=?", (i,), one=True) or abort(404)
    cl = q("SELECT * FROM clients WHERE id=?", (d["client_id"],), one=True) if d["client_id"] else None
    from .pdfgen import document_pdf
    return send_file(document_pdf(d, cl, all_settings()), mimetype="application/pdf", download_name=f"{d['number']}.pdf")


@bp.route("/documenti/<int:i>/stato", methods=["POST"])
@admin_required
def documento_stato(i):
    st = request.form.get("stato")
    if st in DOC_STATI:
        ex("UPDATE documents SET status=? WHERE id=?", (st, i))
    return redirect(request.referrer or url_for("admin.documenti"))


@bp.route("/documenti/<int:i>/elimina", methods=["POST"])
@admin_required
def documento_del(i):
    if q("SELECT 1 FROM payments WHERE document_id=?", (i,), one=True):
        flash("Non si può eliminare un preventivo con acconti registrati: elimina prima gli acconti.")
    else:
        ex("DELETE FROM documents WHERE id=?", (i,))
    return redirect(url_for("admin.documenti"))


@bp.route("/preventivo/<int:i>/crea-preventivo")
@admin_required
def quote_to_doc(i):
    return redirect(url_for("admin.documenti", richiesta=i) + "#nuovo")


# ====================================================================== FATTURE
@bp.route("/fatture")
@admin_required
def fatture():
    year = request.args.get("anno", "")
    stato = request.args.get("stato", "")
    rows = [billing.invoice_view(r) for r in q("SELECT * FROM invoices ORDER BY COALESCE(issue_date,created) DESC, id DESC")]
    if year.isdigit():
        rows = [r for r in rows if (r["issue_date"] or r["created"] or "")[:4] == year]
    if stato:
        rows = [r for r in rows if r["show"] == stato]
    needle = request.args.get("q", "").strip().lower()
    if needle:
        rows = [r for r in rows if needle in (r["number"] or "").lower() or needle in (r["client_name"] or "").lower()]
    allr = [billing.invoice_view(r) for r in q("SELECT * FROM invoices WHERE status IN ('emessa','pagata')")]
    thisy = str(date.today().year)
    cards = dict(emesse=sum(r["total"] for r in allr if (r["issue_date"] or "")[:4] == thisy),
                 incassate=sum(r["paid"] for r in allr if (r["issue_date"] or "")[:4] == thisy),
                 da_incassare=sum(r["resid"] for r in allr if r["show"] in ("emessa", "parziale", "scaduta")),
                 scadute=sum(1 for r in allr if r["show"] == "scaduta"))
    years = sorted({(r["issue_date"] or r["created"] or "")[:4] for r in q("SELECT issue_date, created FROM invoices")} | {thisy}, reverse=True)
    return render_template("admin/fatture.html", rows=rows, cards=cards, years=years, anno=year, stato=stato, fiscal_missing=billing.fiscal_missing())


@bp.route("/fatture/nuova")
@admin_required
def fattura_nuova():
    """Editor di una nuova fattura; `da` precompila da una pratica: appt:ID (appuntamento), quote:ID (richiesta), doc:ID (preventivo), event:ID."""
    da = request.args.get("da", "")
    kind, _, rid = da.partition(":")
    rid = int(rid) if rid.isdigit() else None
    pre = dict(client_id=request.args.get("cliente") if (request.args.get("cliente") or "").isdigit() else None, items=[dict(desc="", qty=1, price=0)], notes="",
               source_type="", source_id=None, event_id=None)
    if kind == "appt" and rid:
        a = q("SELECT * FROM appointments WHERE id=?", (rid,), one=True)
        if a:
            pre.update(client_id=billing.client_for(a["name"], a["phone"], a["email"]), source_type="appt", source_id=rid,
                       notes=f"Evento: {a['event_type']} del {_dmy(a['event_date'])}" if a["event_date"] else "")
    elif kind == "quote" and rid:
        pf = _quote_prefill(str(rid))
        if pf:
            r = pf["quote"]
            pre.update(client_id=pf["client_id"], items=pf["lines"], source_type="quote", source_id=rid,
                       notes=f"{r['event_type']} del {_dmy(r['event_date'])} – {r['place']}".strip(" –"))
    elif kind == "doc" and rid:
        d = q("SELECT * FROM documents WHERE id=?", (rid,), one=True)
        if d:
            pre.update(client_id=d["client_id"], items=json.loads(d["items"] or "[]") or pre["items"], source_type="doc", source_id=rid, notes=f"Rif. preventivo {d['number']}")
    elif kind == "event" and rid:
        e = q("SELECT * FROM events WHERE id=?", (rid,), one=True)
        if e:
            pre.update(client_id=e["client_id"], source_type="event", source_id=rid, event_id=rid, notes=f"{e['title']} – {_dmy(e['date'])} {e['place'] or ''}".strip())
    return render_template("admin/fattura_edit.html", inv=None, pre=pre, f=billing.fiscal(), clients=q("SELECT id,name FROM clients ORDER BY name"),
                           tariffe=q("SELECT * FROM tariffe WHERE active=1 ORDER BY category,name"), events=q("SELECT id,title,date FROM events ORDER BY date DESC LIMIT 60"))


@bp.route("/fatture/<int:i>/modifica")
@admin_required
def fattura_modifica(i):
    inv = q("SELECT * FROM invoices WHERE id=?", (i,), one=True) or abort(404)
    if inv["status"] != "bozza":
        flash("Una fattura emessa non si modifica: annullala e creane una nuova (si può correggere solo scadenza, note e stato SDI dal dettaglio).")
        return redirect(url_for("admin.fattura", i=i))
    pre = dict(client_id=inv["client_id"], items=json.loads(inv["items"] or "[]"), notes=inv["notes"], source_type=inv["source_type"], source_id=inv["source_id"], event_id=inv["event_id"])
    return render_template("admin/fattura_edit.html", inv=inv, pre=pre, f=billing.fiscal(), clients=q("SELECT id,name FROM clients ORDER BY name"),
                           tariffe=q("SELECT * FROM tariffe WHERE active=1 ORDER BY category,name"), events=q("SELECT id,title,date FROM events ORDER BY date DESC LIMIT 60"))


@bp.route("/fatture/salva", methods=["POST"])
@admin_required
def fattura_salva():
    f = request.form
    items = billing.parse_items(f.getlist("desc"), f.getlist("qty"), f.getlist("price"))
    if not items:
        flash("Aggiungi almeno una voce alla fattura.")
        return redirect(request.referrer or url_for("admin.fatture"))
    cid = int(f["client_id"]) if f.get("client_id", "").isdigit() else None
    pct = billing.num(f.get("iva_pct"), float(billing.fiscal()["fat_iva"] or 22))
    imp, iva, tot = billing.totals(items, pct)
    snap = billing.snapshot_client(cid)
    due = f.get("due_date", "") or None
    issue = f.get("issue_date", "") or _today()
    ev = int(f["event_id"]) if f.get("event_id", "").isdigit() else None
    if f.get("id", "").isdigit():
        i = int(f["id"])
        cur = q("SELECT * FROM invoices WHERE id=?", (i,), one=True) or abort(404)
        if cur["status"] != "bozza":
            abort(400)
        ex("""UPDATE invoices SET client_id=?,client_name=?,client_addr=?,client_piva=?,client_cf=?,client_sdi=?,client_pec=?,issue_date=?,due_date=?,items=?,
              imponibile=?,iva_pct=?,iva=?,total=?,notes=?,event_id=? WHERE id=?""",
           (cid, snap["client_name"], snap["client_addr"], snap["client_piva"], snap["client_cf"], snap["client_sdi"], snap["client_pec"], issue, due,
            json.dumps(items, ensure_ascii=False), imp, pct, iva, tot, f.get("notes", "")[:500], ev, i))
    else:
        i = billing.new_invoice(cid, items, f.get("notes", ""), f.get("source_type", ""), int(f["source_id"]) if f.get("source_id", "").isdigit() else None, ev, pct, _by())
        ex("UPDATE invoices SET issue_date=?, due_date=? WHERE id=?", (issue, due, i))
    flash("Bozza di fattura salvata. Controllala, poi premi «Emetti» per assegnare il numero.")
    return redirect(url_for("admin.fattura", i=i))


@bp.route("/fatture/<int:i>")
@admin_required
def fattura(i):
    inv = q("SELECT * FROM invoices WHERE id=?", (i,), one=True) or abort(404)
    v = billing.invoice_view(inv)
    pays = q("SELECT * FROM payments WHERE invoice_id=? ORDER BY date,id", (i,))
    photos = q("SELECT filename,title FROM media WHERE invoice_id=?", (i,))
    return render_template("admin/fattura.html", v=v, pays=pays, f=billing.fiscal(), methods=billing.METHODS, sdi_states=billing.SDI_STATES, photos=photos,
                           today=_today(), missing=billing.fiscal_missing())


@bp.route("/fatture/<int:i>/emetti", methods=["POST"])
@admin_required
def fattura_emetti(i):
    miss = billing.fiscal_missing()
    if miss and request.form.get("forza") != "1":
        flash("Prima di emettere compila i dati fiscali: " + ", ".join(miss) + " (Fatture › Impostazioni fatturazione). Se vuoi emettere comunque, usa «Emetti comunque».")
        return redirect(url_for("admin.fattura", i=i))
    n = billing.issue_invoice(i, _by())
    flash(f"Fattura emessa con il numero {n}." if n else "La fattura non è in bozza.")
    return redirect(url_for("admin.fattura", i=i))


@bp.route("/fatture/<int:i>/stato", methods=["POST"])
@admin_required
def fattura_stato(i):
    inv = q("SELECT * FROM invoices WHERE id=?", (i,), one=True) or abort(404)
    st = request.form.get("stato")
    if st == "pagata" and inv["status"] in ("emessa", "pagata"):
        billing.mark_paid(i, _by())
        flash("Fattura segnata come pagata (registrato l'incasso del residuo).")
    elif st == "annullata" and inv["status"] in ("emessa", "bozza"):
        ex("UPDATE invoices SET status='annullata' WHERE id=?", (i,))
        flash("Fattura annullata. Il numero resta nel registro (non si riusa).")
    elif st == "emessa" and inv["status"] == "pagata":
        ex("UPDATE invoices SET status='emessa' WHERE id=?", (i,))
        billing.sync_invoice_status(i)
    return redirect(url_for("admin.fattura", i=i))


@bp.route("/fatture/<int:i>/dettagli", methods=["POST"])
@admin_required
def fattura_sdi(i):
    inv = q("SELECT * FROM invoices WHERE id=?", (i,), one=True) or abort(404)
    f = request.form
    sdi = f.get("sdi_status") if f.get("sdi_status") in billing.SDI_STATES else inv["sdi_status"]
    due = f.get("due_date") or inv["due_date"]
    ex("UPDATE invoices SET sdi_status=?, sdi_note=?, due_date=?, notes=? WHERE id=?",
       (sdi, f.get("sdi_note", "")[:300], due, f.get("notes", inv["notes"])[:500], i))
    flash("Dati della fattura aggiornati.")
    return redirect(url_for("admin.fattura", i=i))


@bp.route("/fatture/<int:i>.pdf")
@admin_required
def fattura_pdf(i):
    inv = q("SELECT * FROM invoices WHERE id=?", (i,), one=True) or abort(404)
    name = (inv["number"] or f"bozza-{i}").replace("/", "-")
    return send_file(billing.invoice_pdf(inv), mimetype="application/pdf", download_name=f"Fattura-{name}.pdf")


@bp.route("/fatture/<int:i>/elimina", methods=["POST"])
@admin_required
def fattura_elimina(i):
    inv = q("SELECT * FROM invoices WHERE id=?", (i,), one=True) or abort(404)
    if inv["status"] != "bozza":
        flash("Solo le bozze si eliminano. Una fattura emessa si annulla.")
        return redirect(url_for("admin.fattura", i=i))
    ex("DELETE FROM invoices WHERE id=?", (i,))
    flash("Bozza eliminata.")
    return redirect(url_for("admin.fatture"))


@bp.route("/fatture/impostazioni", methods=["GET", "POST"])
@admin_required
def fatture_impostazioni():
    if request.method == "POST":
        for k, _l, _t in billing.FISCAL_FIELDS:
            if k in request.form:
                set_setting(k, request.form.get(k, "").strip()[:400])
        flash("Impostazioni di fatturazione salvate.")
        return redirect(url_for("admin.fatture_impostazioni"))
    nxt = billing.next_number()
    return render_template("admin/fatt_impostazioni.html", fields=billing.FISCAL_FIELDS, f=billing.fiscal(), nxt=nxt[1], missing=billing.fiscal_missing())


# ====================================================================== ACCONTI
@bp.route("/acconti")
@admin_required
def acconti():
    month = request.args.get("mese", _today()[:7])
    pays = q("""SELECT p.*, i.number inv_number, d.number doc_number, e.title ev_title FROM payments p LEFT JOIN invoices i ON i.id=p.invoice_id
                LEFT JOIN documents d ON d.id=p.document_id LEFT JOIN events e ON e.id=p.event_id
                WHERE (?='' OR substr(p.date,1,7)=?) ORDER BY p.date DESC, p.id DESC LIMIT 300""", (month if month != "tutti" else "", month if month != "tutti" else ""))
    year = _today()[:4]
    cards = dict(mese=q("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE substr(date,1,7)=?", (_today()[:7],), one=True)["s"],
                 anno=q("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE substr(date,1,4)=?", (year,), one=True)["s"])
    targets, open_rows = [], []
    for r in q("SELECT d.*, c.name client FROM documents d LEFT JOIN clients c ON c.id=d.client_id WHERE d.kind='preventivo' AND d.status IN ('inviato','accettato') ORDER BY d.id DESC"):
        paid = billing.paid_of("document", r["id"])
        targets.append(("doc:%d" % r["id"], f"Preventivo {r['number']} – {r['client'] or ''} (€ {billing.eur(r['total'])}, versato € {billing.eur(paid)})"))
        open_rows.append(dict(kind="Preventivo", number=r["number"], client=r["client"], total=r["total"], paid=paid, resid=round(r["total"] - paid, 2),
                              state="saldato" if paid + 0.005 >= r["total"] > 0 else ("parziale" if paid > 0 else "da versare"), url=url_for("admin.documenti") + f"#d{r['id']}"))
    for r in q("SELECT * FROM invoices WHERE status IN ('emessa','pagata') ORDER BY id DESC"):
        v = billing.invoice_view(r)
        targets.append(("inv:%d" % r["id"], f"Fattura {r['number']} – {r['client_name']} (€ {billing.eur(r['total'])}, residuo € {billing.eur(v['resid'])})"))
        open_rows.append(dict(kind="Fattura", number=r["number"], client=r["client_name"], total=r["total"], paid=v["paid"], resid=v["resid"],
                              state={"pagata": "saldato", "parziale": "parziale", "scaduta": "scaduta"}.get(v["show"], "da versare"), url=url_for("admin.fattura", i=r["id"])))
    for r in q("SELECT * FROM events WHERE status!='annullato' AND date>=date('now','-60 day') ORDER BY date DESC"):
        targets.append(("evt:%d" % r["id"], f"Evento {r['title']} ({_dmy(r['date'])})"))
    pre = request.args.get("doc") and "doc:" + request.args["doc"] or (request.args.get("fattura") and "inv:" + request.args["fattura"]) or (request.args.get("evento") and "evt:" + request.args["evento"]) or ""
    return render_template("admin/acconti.html", pays=pays, cards=cards, targets=targets, open_rows=open_rows, methods=billing.METHODS, mese=month, pre=pre, today=_today())


@bp.route("/acconti/nuovo", methods=["POST"])
@admin_required
def acconto_nuovo():
    f = request.form
    amount = billing.num(f.get("amount"), 0)
    if amount <= 0:
        flash("Inserisci un importo maggiore di zero.")
        return redirect(request.referrer or url_for("admin.acconti"))
    kind, _, rid = (f.get("target") or "").partition(":")
    if not rid.isdigit() or kind not in ("inv", "doc", "evt"):
        flash("Scegli a cosa si riferisce il pagamento.")
        return redirect(request.referrer or url_for("admin.acconti"))
    day = f.get("date") or _today()
    billing.add_payment(amount, f.get("method", "bonifico"), f.get("note", ""), day, invoice_id=int(rid) if kind == "inv" else None,
                        document_id=int(rid) if kind == "doc" else None, event_id=int(rid) if kind == "evt" else None, user=_by())
    flash(f"Registrato un incasso di € {billing.eur(amount)}.")
    back = request.form.get("back") or url_for("admin.acconti")
    return redirect(back if back.startswith("/admin/") else url_for("admin.acconti"))


@bp.route("/acconti/<int:i>/elimina", methods=["POST"])
@admin_required
def acconto_elimina(i):
    billing.delete_payment(i)
    flash("Incasso eliminato.")
    back = request.form.get("back") or url_for("admin.acconti")
    return redirect(back if back.startswith("/admin/") else url_for("admin.acconti"))


# ====================================================================== TARIFFE
TAR_UNITS = ["a evento", "a serata", "al mq", "all'ora", "al giorno", "a pezzo"]
TAR_CATS = ["Audio", "Luci", "Ledwall / Video", "Allestimenti", "Personale", "Trasporto", "Altro"]


@bp.route("/tariffe", methods=["GET", "POST"])
@admin_required
def tariffe():
    if request.method == "POST":
        f = request.form
        if f.get("pubbliche_toggle"):
            set_setting("tariffe_pubbliche", "1" if f.get("tariffe_pubbliche") else "0")
        else:
            ex("INSERT INTO tariffe(name,category,service,unit,price,note,active,public,sort) VALUES(?,?,?,?,?,?,?,?,?)",
               (f.get("name", "")[:100], f.get("category", "Altro"), f.get("service", ""), f.get("unit", "a evento"), billing.num(f.get("price"), 0),
                f.get("note", "")[:200], 1, int(bool(f.get("public"))), 999))
        flash("Tariffa aggiunta.") if not f.get("pubbliche_toggle") else flash("Impostazione salvata.")
        return redirect(url_for("admin.tariffe"))
    return render_template("admin/tariffe.html", rows=q("SELECT * FROM tariffe ORDER BY active DESC, category, sort, name"), units=TAR_UNITS, cats=TAR_CATS,
                           services=SERVICES, pubbliche=get_setting("tariffe_pubbliche", "0") == "1")


@bp.route("/tariffe/<int:i>", methods=["POST"])
@admin_required
def tariffa_salva(i):
    f = request.form
    ex("UPDATE tariffe SET name=?,category=?,service=?,unit=?,price=?,note=?,active=?,public=? WHERE id=?",
       (f.get("name", "")[:100], f.get("category", "Altro"), f.get("service", ""), f.get("unit", "a evento"), billing.num(f.get("price"), 0),
        f.get("note", "")[:200], int(bool(f.get("active"))), int(bool(f.get("public"))), i))
    flash("Tariffa salvata.")
    return redirect(url_for("admin.tariffe") + f"#t{i}")


@bp.route("/tariffe/<int:i>/elimina", methods=["POST"])
@admin_required
def tariffa_elimina(i):
    ex("DELETE FROM tariffe WHERE id=?", (i,))
    return redirect(url_for("admin.tariffe"))


# ====================================================================== STATISTICHE
@bp.route("/statistiche")
@admin_required
def statistiche():
    y = request.args.get("anno", _today()[:4])
    if not y.isdigit():
        y = _today()[:4]
    months = [q("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE substr(date,1,7)=?", (f"{y}-{m:02d}",), one=True)["s"] for m in range(1, 13)]
    years = [(r["y"], r["s"]) for r in q("SELECT substr(date,1,4) y, SUM(amount) s FROM payments GROUP BY y ORDER BY y DESC LIMIT 6")]
    by_method = q("SELECT method, SUM(amount) s FROM payments WHERE substr(date,1,4)=? GROUP BY method ORDER BY s DESC", (y,))
    # eventi per tipo: eventi in calendario + appuntamenti confermati/completati (non annullati)
    types = {}
    for r in q("SELECT event_type t FROM events WHERE substr(date,1,4)=? AND status!='annullato'", (y,)):
        types[r["t"] or "Non indicato"] = types.get(r["t"] or "Non indicato", 0) + 1
    for r in q("SELECT event_type t FROM appointments WHERE substr(event_date,1,4)=? AND status IN ('confermato','completato')", (y,)):
        types[r["t"] or "Non indicato"] = types.get(r["t"] or "Non indicato", 0) + 1
    svc = {}
    for r in q("SELECT services FROM quotes WHERE substr(created,1,4)=?", (y,)):
        for s in [x.strip() for x in (r["services"] or "").split(",") if x.strip()]:
            svc[s] = svc.get(s, 0) + 1
    n_q = q("SELECT COUNT(*) c FROM quotes WHERE substr(created,1,4)=?", (y,), one=True)["c"]
    n_a = q("SELECT COUNT(*) c FROM appointments WHERE substr(created,1,4)=? AND status!='annullato'", (y,), one=True)["c"]
    conf_q = q("SELECT COUNT(*) c FROM quotes WHERE substr(created,1,4)=? AND status='confermata'", (y,), one=True)["c"]
    conf_a = q("SELECT COUNT(*) c FROM appointments WHERE substr(created,1,4)=? AND status IN ('confermato','completato')", (y,), one=True)["c"]
    tot, conf = n_q + n_a, conf_q + conf_a
    funnel = dict(totale=tot, preventivi=n_q, appuntamenti=n_a, confermati=conf, perc=round(100 * conf / tot, 1) if tot else 0)
    return render_template("admin/statistiche.html", y=y, months=months, mesi=[m[:3].title() for m in MESI], mx=max(months + [1]), years=years, by_method=by_method,
                           types=sorted(types.items(), key=lambda x: -x[1]), svc=sorted(svc.items(), key=lambda x: -x[1]), funnel=funnel, tot_anno=sum(months))


# ====================================================================== WHATSAPP
def _summary_text(kind, i):
    if kind == "appuntamento":
        a = q("SELECT * FROM appointments WHERE id=?", (i,), one=True) or abort(404)
        return (f"📅 Appuntamento ({a['status']})\n{a['name']} – {a['phone']}\n{_dmy(a['slot_date'])} alle {a['slot_time']}\n"
                f"Evento: {a['event_type']} il {_dmy(a['event_date'])}\nNote: {a['notes'] or '—'}")
    r = q("SELECT * FROM quotes WHERE id=?", (i,), one=True) or abort(404)
    return (f"🆕 Richiesta preventivo ({r['status']})\n{r['name']} – {r['phone']}\n{r['event_type']} il {_dmy(r['event_date'])} a {r['place']}, {r['guests']} ospiti\n"
            f"Servizi: {r['services']}\nNote: {r['notes'] or '—'}")


@bp.route("/richieste/<kind>/<int:i>/whatsapp", methods=["POST"])
@admin_required
def wa_riepilogo(kind, i):
    if kind not in ("appuntamento", "preventivo"):
        abort(404)
    text = _summary_text(kind, i)
    num = notify.normalize_number(request.form.get("numero", ""))
    if not notify.twilio_ready():
        flash("⚠️ WhatsApp (Twilio) non è configurato: apri WhatsApp › Impostazioni. Intanto puoi copiare il riepilogo.")
        return redirect(request.referrer or url_for("admin.richieste"))
    res = notify.send_many([num], text, "manual_summary") if num else notify.notify_duty(text, "manual_summary")
    ok = res.get("sent", 0) > 0
    flash(("✅ Riepilogo inviato su WhatsApp a %d persona/e." % res["sent"]) if ok else "⚠️ Invio non riuscito: " + "; ".join(res.get("errors") or ["nessun destinatario di turno (Team e contatti)"]))
    return redirect(request.referrer or url_for("admin.richieste"))


@bp.route("/whatsapp")
@admin_required
def whatsapp():
    rec = {"duty": len(notify.recipients("duty")), "report": len(notify.recipients("report:daily"))}
    return render_template("admin/whatsapp.html", tw_ready=notify.twilio_ready(), sender=notify.cfg("twilio_whatsapp_from"), rec=rec, vapi=notify.vapi_ready(),
                           flag=notify.flag("wa_notify_requests", "1"), log=q("SELECT * FROM wa_log ORDER BY id DESC LIMIT 25"),
                           sent7=q("SELECT COUNT(*) c FROM wa_log WHERE ok=1 AND ts>=datetime('now','-7 day')", one=True)["c"],
                           err7=q("SELECT COUNT(*) c FROM wa_log WHERE ok=0 AND ts>=datetime('now','-7 day')", one=True)["c"])


# ====================================================================== UTENTI E REGISTRO
def _pw_ok(p):
    return len(p or "") >= 10


def _gen_pw():
    return secrets.token_urlsafe(9)


@bp.route("/utenti")
@admin_required
def utenti():
    rows = q("SELECT * FROM admin_users ORDER BY active DESC, role, username")
    return render_template("admin/utenti.html", rows=rows, roles=rbac.ROLES, new=session.pop("new_pw", None))


@bp.route("/utenti/crea", methods=["POST"])
@admin_required
def utente_crea():
    f = request.form
    un = re.sub(r"[^a-z0-9._-]", "", (f.get("username", "").strip().lower()))[:30]
    role = f.get("role") if f.get("role") in rbac.ROLES else rbac.COLLAB
    if len(un) < 3 or q("SELECT 1 FROM admin_users WHERE username=?", (un,), one=True):
        flash("Nome utente non valido o già esistente (almeno 3 caratteri: lettere, numeri, . _ -).")
        return redirect(url_for("admin.utenti"))
    pw = f.get("password", "").strip() or _gen_pw()
    if not _pw_ok(pw):
        flash("La password deve avere almeno 10 caratteri (oppure lasciala vuota: ne creo una io).")
        return redirect(url_for("admin.utenti"))
    ex("INSERT INTO admin_users(username,pw_hash,role,active,name,email,must_change,created) VALUES(?,?,?,?,?,?,?,datetime('now'))",
       (un, generate_password_hash(pw), role, 1, f.get("name", "")[:60], f.get("email", "")[:100], 1))
    session["new_pw"] = {"username": un, "password": pw}
    audit("Utente creato", f"{un} ({role})")
    return redirect(url_for("admin.utenti"))


def _active_admins():
    return q("SELECT COUNT(*) c FROM admin_users WHERE role='admin' AND active=1", one=True)["c"]


@bp.route("/utenti/<int:i>/modifica", methods=["POST"])
@admin_required
def utente_modifica(i):
    u = q("SELECT * FROM admin_users WHERE id=?", (i,), one=True) or abort(404)
    f = request.form
    role = f.get("role") if f.get("role") in rbac.ROLES else u["role"]
    if u["role"] == rbac.ADMIN and role != rbac.ADMIN and u["active"] and _active_admins() <= 1:
        flash("Deve restare almeno un amministratore attivo.")
        return redirect(url_for("admin.utenti"))
    ex("UPDATE admin_users SET name=?,email=?,role=? WHERE id=?", (f.get("name", "")[:60], f.get("email", "")[:100], role, i))
    flash("Utente aggiornato.")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:i>/attiva", methods=["POST"])
@admin_required
def utente_attiva(i):
    u = q("SELECT * FROM admin_users WHERE id=?", (i,), one=True) or abort(404)
    me = current_user()
    new = 0 if u["active"] else 1
    if not new and (u["id"] == me["id"] or (u["role"] == rbac.ADMIN and _active_admins() <= 1)):
        flash("Non puoi disattivare te stesso né l'ultimo amministratore attivo.")
        return redirect(url_for("admin.utenti"))
    ex("UPDATE admin_users SET active=? WHERE id=?", (new, i))
    flash("Utente attivato." if new else "Utente disattivato: non può più accedere.")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:i>/reset", methods=["POST"])
@admin_required
def utente_reset(i):
    u = q("SELECT * FROM admin_users WHERE id=?", (i,), one=True) or abort(404)
    pw = _gen_pw()
    ex("UPDATE admin_users SET pw_hash=?, must_change=1 WHERE id=?", (generate_password_hash(pw), i))
    session["new_pw"] = {"username": u["username"], "password": pw}
    return redirect(url_for("admin.utenti"))


@bp.route("/registro")
@admin_required
def registro():
    who, act = request.args.get("utente", ""), request.args.get("azione", "")
    rows = q("""SELECT * FROM audit_log WHERE (?='' OR username=?) AND (?='' OR action LIKE ?) ORDER BY id DESC LIMIT 300""", (who, who, act, f"%{act}%"))
    return render_template("admin/registro.html", rows=rows, users=[r["username"] for r in q("SELECT DISTINCT username FROM audit_log WHERE username!='' ORDER BY username")],
                           who=who, act=act)


# ====================================================================== BACKUP (stato)
@bp.route("/backup")
@admin_required
def backup():
    info, age = {}, None
    p = DATA / "backup-status.txt"
    try:
        for ln in p.read_text(encoding="utf-8").splitlines():
            if "=" in ln:
                k, _, v = ln.partition("=")
                info[k.strip()] = v.strip()
        t = datetime.fromisoformat(info["time"])
        age = round((datetime.now(t.tzinfo) - t).total_seconds() / 3600, 1)
    except (OSError, KeyError, ValueError):
        pass
    return render_template("admin/backup.html", info=info, age=age, ok=(age is not None and age < 26))
