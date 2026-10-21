"""Recensioni: richiesta post-evento (email con link personale), pagina pubblica per scriverla, approvazione e pubblicazione dall'admin.

Flusso:  evento/appuntamento svolto → email «com'è andata?» con link /recensione/<token> → il cliente scrive stelle + testo →
stato «in attesa» → l'admin approva → compare nel sito (stelle, nome, evento). Nulla viene pubblicato senza approvazione.
"""
import os
import secrets
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash, abort, jsonify

from .admin import bp
from .db import q, ex, get_setting, set_setting
from .mailer import send_mail
from .public import bp as pub
from .rbac import audit
from .security import admin_required, check_csrf, csrf_token

STATI = ["richiesta", "in attesa", "approvata", "rifiutata"]


def public_base():
    """URL pubblico del sito per i link nelle email: PUBLIC_URL (.env) o «Sito ufficiale» in Testi, altrimenti l'indirizzo della richiesta in corso."""
    u = os.getenv("PUBLIC_URL", "").strip() or get_setting("sito_url", "").strip()
    if not u and request:
        u = request.host_url
    return u.rstrip("/")


def create_request(author, email, event="", ref_type="", ref_id=None, send=True):
    """Crea la richiesta (token personale) e, se c'è un'email, la invia. Ritorna (id, link, inviata)."""
    token = secrets.token_urlsafe(18)
    rid = ex("INSERT INTO reviews(author,text,source,hidden,status,token,email,event,ref_type,ref_id,requested_at,created,stars) VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'),5)",
             (author[:80], "", "richiesta via email", 1, "richiesta", token, email[:120], event[:100], ref_type, ref_id))
    base = public_base()
    link = f"{base}/recensione/{token}" if base else f"/recensione/{token}"
    sent = False
    if send and email:
        brand = get_setting("brand_short", "") or get_setting("brand", "LMC Service")
        sent = bool(send_mail(email, f"Com'è andato il tuo evento? Lascia una recensione – {brand}",
                              f"Ciao {author or ''},\ngrazie per aver scelto {brand}{' per ' + event if event else ''}!\n"
                              f"Ci aiuta moltissimo sapere com'è andata: bastano 30 secondi.\n\nScrivi la tua recensione: {link}\n\n"
                              f"La leggeremo noi prima di pubblicarla. Grazie!\n{brand}"))
    return rid, link, sent


def auto_requests():
    """Ogni ora: per gli eventi/appuntamenti svolti negli ultimi 14 giorni (con email) invia UNA richiesta di recensione. Spegnibile da Recensioni."""
    if get_setting("review_auto", "1") != "1" or not (os.getenv("PUBLIC_URL", "").strip() or get_setting("sito_url", "").strip()):
        return 0
    n, today = 0, date.today()
    lo, hi = (today - timedelta(days=14)).isoformat(), (today - timedelta(days=1)).isoformat()
    for e in q("""SELECT e.id, e.title, c.name, c.email FROM events e JOIN clients c ON c.id=e.client_id
                  WHERE e.date BETWEEN ? AND ? AND e.status!='annullato' AND c.email!='' """, (lo, hi)):
        if not q("SELECT 1 FROM reviews WHERE ref_type='event' AND ref_id=?", (e["id"],), one=True):
            create_request(e["name"] or "", e["email"], e["title"] or "", "event", e["id"])
            n += 1
    for a in q("SELECT id,name,email,event_type FROM appointments WHERE event_date BETWEEN ? AND ? AND status IN ('confermato','completato') AND email!=''", (lo, hi)):
        if not q("SELECT 1 FROM reviews WHERE ref_type='appt' AND ref_id=?", (a["id"],), one=True):
            create_request(a["name"], a["email"], a["event_type"] or "", "appt", a["id"])
            n += 1
    return n


# ------------------------------------------------------------------ pubblico
@pub.route("/recensione/<token>", methods=["GET", "POST"])
def recensione(token):
    r = q("SELECT * FROM reviews WHERE token=?", (token,), one=True)
    if not r:
        abort(404)
    from .public import ctx
    msg, done = "", r["status"] in ("in attesa", "approvata", "rifiutata")
    if request.method == "POST" and not done:
        check_csrf()
        f = request.form
        text = f.get("text", "").strip()[:800]
        author = f.get("author", "").strip()[:80] or r["author"] or "Cliente"
        try:
            stars = max(1, min(5, int(f.get("stars", "5"))))
        except ValueError:
            stars = 5
        if len(text) < 10:
            msg = "Scrivi almeno una breve frase (10 caratteri)."
        elif not f.get("consent"):
            msg = "Serve il consenso alla pubblicazione della recensione con il tuo nome."
        else:
            ex("UPDATE reviews SET text=?, author=?, stars=?, status='in attesa', hidden=1, source='dal sito' WHERE id=?", (text, author, stars, r["id"]))
            try:
                send_mail(os.getenv("OWNER_EMAIL"), f"Nuova recensione da approvare: {author} ({stars}★)", f"{author} ha scritto:\n\n{text}\n\nApprovala da Admin › Recensioni.")
            except Exception:
                pass
            r = q("SELECT * FROM reviews WHERE token=?", (token,), one=True)
            done = True
    return render_template("recensione.html", r=r, s=ctx(), msg=msg, done=done, csrf=csrf_token())


# ------------------------------------------------------------------ admin
@bp.route("/recensioni")
@admin_required
def recensioni():
    tab = request.args.get("t", "in attesa")
    rows = q("SELECT * FROM reviews WHERE status=? ORDER BY id DESC", (tab,)) if tab in STATI else q("SELECT * FROM reviews ORDER BY id DESC")
    counts = {s: q("SELECT COUNT(*) c FROM reviews WHERE status=?", (s,), one=True)["c"] for s in STATI}
    return render_template("admin/recensioni.html", rows=rows, tab=tab, counts=counts, auto=get_setting("review_auto", "1") == "1",
                           base=public_base(), base_ok=bool(os.getenv("PUBLIC_URL", "").strip() or get_setting("sito_url", "").strip()),
                           apps=q("SELECT id,name,email,event_type,event_date FROM appointments WHERE status IN ('confermato','completato') ORDER BY slot_date DESC LIMIT 40"),
                           events=q("SELECT e.id,e.title,e.date,c.name,c.email FROM events e LEFT JOIN clients c ON c.id=e.client_id ORDER BY e.date DESC LIMIT 40"),
                           link=request.args.get("link", ""))


@bp.route("/recensioni/richiedi", methods=["POST"])
@admin_required
def recensione_richiedi():
    f = request.form
    kind, _, rid = (f.get("da") or "").partition(":")
    author, email, event = f.get("author", "").strip(), f.get("email", "").strip(), f.get("event", "").strip()
    ref_id = int(rid) if rid.isdigit() else None
    if kind == "appt" and ref_id:
        a = q("SELECT * FROM appointments WHERE id=?", (ref_id,), one=True)
        if a:
            author, email, event = a["name"], a["email"], a["event_type"] or ""
    elif kind == "event" and ref_id:
        e = q("SELECT e.title, c.name, c.email FROM events e LEFT JOIN clients c ON c.id=e.client_id WHERE e.id=?", (ref_id,), one=True)
        if e:
            author, email, event = e["name"] or author, e["email"] or email, e["title"] or ""
    if not author and not email:
        flash("Scegli un evento/appuntamento oppure scrivi nome ed email del cliente.")
        return redirect(url_for("admin.recensioni"))
    _id, link, sent = create_request(author, email, event, kind if kind in ("appt", "event") else "", ref_id)
    flash(("✅ Email inviata a %s." % email) if sent else "Richiesta creata (nessuna email inviata: copia il link e mandalo tu, per esempio su WhatsApp).")
    return redirect(url_for("admin.recensioni", t="richiesta", link=link))


@bp.route("/recensioni/<int:i>/stato", methods=["POST"])
@admin_required
def recensione_stato(i):
    st = request.form.get("stato")
    if st not in STATI:
        abort(400)
    ex("UPDATE reviews SET status=?, hidden=? WHERE id=?", (st, 0 if st == "approvata" else 1, i))
    flash({"approvata": "Recensione approvata: ora è visibile sul sito.", "rifiutata": "Recensione rifiutata (non compare sul sito)."}.get(st, "Stato aggiornato."))
    return redirect(url_for("admin.recensioni", t=request.form.get("t", "in attesa")))


@bp.route("/recensioni/<int:i>/modifica", methods=["POST"])
@admin_required
def recensione_modifica(i):
    f = request.form
    try:
        stars = max(1, min(5, int(f.get("stars", "5"))))
    except ValueError:
        stars = 5
    ex("UPDATE reviews SET author=?, text=?, stars=?, event=? WHERE id=?", (f.get("author", "")[:80], f.get("text", "")[:800], stars, f.get("event", "")[:100], i))
    flash("Recensione modificata.")
    return redirect(url_for("admin.recensioni", t=request.form.get("t", "in attesa")))


@bp.route("/recensioni/<int:i>/elimina", methods=["POST"])
@admin_required
def recensione_elimina(i):
    ex("DELETE FROM reviews WHERE id=?", (i,))
    return redirect(url_for("admin.recensioni", t=request.form.get("t", "in attesa")))


@bp.route("/recensioni/aggiungi", methods=["POST"])
@admin_required
def recensione_aggiungi():
    """Recensione ricevuta altrove (Google, Facebook, a voce): la inserisce il titolare, già approvata."""
    f = request.form
    if not f.get("author", "").strip() or len(f.get("text", "").strip()) < 10:
        flash("Servono nome e testo della recensione.")
        return redirect(url_for("admin.recensioni"))
    try:
        stars = max(1, min(5, int(f.get("stars", "5"))))
    except ValueError:
        stars = 5
    ex("INSERT INTO reviews(author,text,source,hidden,status,stars,event,created) VALUES(?,?,?,?,?,?,?,datetime('now'))",
       (f["author"].strip()[:80], f["text"].strip()[:800], f.get("source", "")[:60], 0, "approvata", stars, f.get("event", "")[:100]))
    flash("Recensione pubblicata sul sito.")
    return redirect(url_for("admin.recensioni", t="approvata"))


@bp.route("/recensioni/automatiche", methods=["POST"])
@admin_required
def recensioni_auto():
    if request.form.get("run"):
        n = auto_requests()
        flash(f"Richieste inviate ora: {n}.")
    else:
        set_setting("review_auto", "1" if request.form.get("auto") else "0")
        flash("Impostazione salvata.")
    return redirect(url_for("admin.recensioni"))
