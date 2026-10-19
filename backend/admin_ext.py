"""Admin: Impostazioni (WhatsApp/Twilio, Vapi, report, emergenza) e pagina Report."""
import json
import secrets
import urllib.error
import urllib.request

from flask import render_template, request, redirect, url_for, flash

from .admin import bp
from .db import q, ex, get_setting, set_setting, set_secret
from .security import admin_required
from . import notify, reports, metrics

PLAIN = ["twilio_account_sid", "twilio_whatsapp_from", "twilio_content_sid", "wa_destinations",
         "vapi_public_key", "vapi_assistant_id", "vapi_emergency_assistant_id",
         "emergency_number", "emergency_hours"]
SECRET = ["twilio_auth_token", "vapi_api_key", "vapi_webhook_secret"]   # campi write-only: non si rivelano mai
TOGGLES = ["wa_notify_requests", "emergency_on", "report_daily_on", "report_weekly_on", "report_monthly_on"]
TIMES = ["report_daily_time", "report_weekly_time", "report_monthly_time"]


def _vapi_get(path, key, timeout=8):
    """GET sulle API Vapi (isolato per i test)."""
    req = urllib.request.Request("https://api.vapi.ai" + path, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {}
    except (urllib.error.URLError, OSError, ValueError) as e:
        return 0, {"message": str(e)}


def _view():
    team = q("SELECT * FROM team ORDER BY sort, id")
    sel = {k: ({int(x) for x in get_setting(f"report_{k}_to", "").split(",") if x.strip().isdigit()} if get_setting(f"report_{k}_to", "") else None)
           for k in reports.KINDS}
    return dict(
        team=team, sel=sel, src={k: notify.source(k) for k in notify.ENV},
        plain={k: get_setting(k, "") for k in PLAIN}, secret_set={k: bool(notify.cfg(k)) for k in SECRET},
        tog={k: (get_setting(k, "1" if k in ("wa_notify_requests", "emergency_on", "report_daily_on") else "0") == "1") for k in TOGGLES},
        times={k: get_setting(k, reports.DEFAULT_TIME[k.split("_")[1]]) for k in TIMES},
        tw_ready=notify.twilio_ready(), vapi_ready=notify.vapi_ready(),
        wa_log=q("SELECT * FROM wa_log ORDER BY id DESC LIMIT 8"), webhook=request.host_url.rstrip("/") + "/webhook/vapi")


@bp.route("/impostazioni")
@admin_required
def impostazioni():
    return render_template("admin/impostazioni.html", **_view())


@bp.route("/impostazioni/salva", methods=["POST"])
@admin_required
def impostazioni_salva():
    f = request.form
    sec = f.get("sezione", "")
    keys = {"wa": ["twilio_account_sid", "twilio_whatsapp_from", "twilio_content_sid", "wa_destinations"],
            "vapi": ["vapi_public_key", "vapi_assistant_id", "vapi_emergency_assistant_id"],
            "emergenza": ["emergency_number", "emergency_hours"]}.get(sec, [])
    for k in keys:
        set_setting(k, f.get(k, "").strip()[:600])
    for k in SECRET:
        if k.split("_")[0] != {"wa": "twilio", "vapi": "vapi"}.get(sec, "-"):
            continue
        if f.get(f"clear_{k}"):
            set_secret(k, "")
        elif f.get(k, "").strip():
            set_secret(k, f[k].strip()[:600])
    if sec == "wa":
        set_setting("wa_notify_requests", "1" if f.get("wa_notify_requests") else "0")
    if sec == "emergenza":
        set_setting("emergency_on", "1" if f.get("emergency_on") else "0")
    if sec == "report":
        for k in reports.KINDS:
            set_setting(f"report_{k}_on", "1" if f.get(f"report_{k}_on") else "0")
            t = f.get(f"report_{k}_time", "").strip()
            if len(t) == 5 and t[2] == ":" and t[:2].isdigit() and t[3:].isdigit():
                set_setting(f"report_{k}_time", t)
            ids = [x for x in f.getlist(f"report_{k}_to") if x.isdigit()]
            set_setting(f"report_{k}_to", ",".join(ids) if ids else "none")
    flash("Impostazioni salvate.")
    return redirect(url_for("admin.impostazioni") + (f"#{sec}" if sec else ""))


@bp.route("/impostazioni/webhook-secret", methods=["POST"])
@admin_required
def genera_webhook_secret():
    set_secret("vapi_webhook_secret", secrets.token_urlsafe(24))
    flash("Nuovo secret per il webhook Vapi generato. Copialo nel campo 'Server URL secret' di Vapi (è nell'header X-Vapi-Secret).")
    return redirect(url_for("admin.impostazioni") + "#vapi")


@bp.route("/impostazioni/test/<what>", methods=["POST"])
@admin_required
def impostazioni_test(what):
    if what == "twilio":
        ok, msg = notify.twilio_check()
    elif what == "whatsapp":
        nums = [notify.normalize_number(request.form.get("numero", ""))] if request.form.get("numero", "").strip() else notify.recipients("duty")
        nums = [n for n in nums if n]
        if not nums:
            ok, msg = False, "Nessun destinatario: aggiungi un numero in Team e Contatti o nel campo qui sotto."
        else:
            r = notify.send_many(nums, "✅ Test da LMC Service: la connessione WhatsApp funziona.", "test")
            ok = r["sent"] > 0
            msg = (f"Messaggio inviato a {r['sent']} numero/i." if ok else "Invio non riuscito: " + "; ".join(r["errors"] or ["Twilio non configurato"]))
            if ok:
                msg += " (Con il sandbox Twilio il destinatario deve aver prima inviato il codice 'join …' al numero sandbox.)"
    elif what == "vapi":
        key, aid = notify.cfg("vapi_api_key"), notify.cfg("vapi_assistant_id")
        if not (key and aid):
            ok, msg = False, "Inserisci la API key privata e l'Assistant ID."
        else:
            st, js = _vapi_get(f"/assistant/{aid}", key)
            ok = st == 200
            msg = f"Assistente trovato: {js.get('name') or aid}." if ok else f"Vapi ha risposto {st}: {js.get('message', 'controlla chiave e ID')}"
    else:
        return redirect(url_for("admin.impostazioni"))
    flash(("✅ " if ok else "⚠️ ") + msg)
    return redirect(url_for("admin.impostazioni") + {"twilio": "#wa", "whatsapp": "#wa", "vapi": "#vapi"}[what])


@bp.route("/report")
@admin_required
def report():
    today = metrics.now_local().date()
    from datetime import timedelta
    iso = lambda d: d.isoformat()
    cards = [("Oggi", reports.stats(iso(today), iso(today))),
             ("Ieri", reports.stats(iso(today - timedelta(days=1)), iso(today - timedelta(days=1)))),
             ("Ultimi 7 giorni", reports.stats(iso(today - timedelta(days=6)), iso(today))),
             ("Ultimi 30 giorni", reports.stats(iso(today - timedelta(days=29)), iso(today)))]
    days = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        s = reports.stats(iso(d), iso(d))
        days.append((d, s))
    mx = max([s["visits"] for _d, s in days] + [1])
    prev = {k: reports.build_text(k) for k in reports.KINDS}
    return render_template("admin/report.html", cards=cards, days=days, mx=mx, prev=prev, giorni=reports.GIORNI, log=reports.recent_log(),
                           enabled={k: reports.enabled(k) for k in reports.KINDS}, tw_ready=notify.twilio_ready(),
                           recips={k: len(notify.recipients(f"report:{k}")) for k in reports.KINDS})


@bp.route("/report/invia", methods=["POST"])
@admin_required
def report_invia():
    kind = request.form.get("tipo")
    if kind not in reports.KINDS:
        return redirect(url_for("admin.report"))
    if not notify.twilio_ready():
        flash("⚠️ WhatsApp non è configurato: apri Impostazioni › WhatsApp / Twilio.")
    else:
        ok, detail, _t = reports.send_now(kind)
        flash(("✅ " if ok else "⚠️ ") + f"Report {kind}: {detail}")
    return redirect(url_for("admin.report"))
