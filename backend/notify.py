"""Configurazione chiavi (database o .env), invio WhatsApp via Twilio REST, destinatari e rate limit.

Nessuna chiave è nel codice: ogni valore si legge da Admin › Impostazioni (tabella settings) oppure dal .env.
Il valore salvato in admin ha la precedenza; se è vuoto si usa la variabile d'ambiente.
"""
import base64
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .db import q, ex, get_setting, get_secret

# chiave nel database -> variabile d'ambiente
ENV = {
    "twilio_account_sid": "TWILIO_ACCOUNT_SID", "twilio_auth_token": "TWILIO_AUTH_TOKEN",
    "twilio_whatsapp_from": "TWILIO_WHATSAPP_FROM", "twilio_content_sid": "TWILIO_CONTENT_SID",
    "wa_destinations": "WHATSAPP_DESTINATIONS",
    "vapi_api_key": "VAPI_API_KEY", "vapi_public_key": "VAPI_PUBLIC_KEY", "vapi_assistant_id": "VAPI_ASSISTANT_ID",
    "vapi_emergency_assistant_id": "VAPI_EMERGENCY_ASSISTANT_ID", "vapi_webhook_secret": "VAPI_WEBHOOK_SECRET",
}
SECRETS = {"twilio_auth_token", "vapi_api_key", "vapi_webhook_secret"}   # mai restituiti all'interfaccia
WA_LIMIT = 1500                                                          # WhatsApp accetta max 1600 caratteri


def _stored(key):
    return (get_secret(key, "") if key in SECRETS else get_setting(key, "")) or ""


def cfg(key, default=""):
    v = _stored(key).strip()
    return v or os.getenv(ENV.get(key, ""), "").strip() or default


def source(key):
    """'admin' | 'env' | '' : da dove arriva il valore (per mostrarlo in Impostazioni senza rivelarlo)."""
    if _stored(key).strip():
        return "admin"
    return "env" if os.getenv(ENV.get(key, ""), "").strip() else ""


def flag(key, default="1"):
    return (get_setting(key, default) or default) == "1"


def normalize_number(n):
    """'+39 366 178 2548', '0039 366…', '3661782548', '393661782548' -> '+393661782548'. Vuoto se non plausibile."""
    d = re.sub(r"[^\d+]", "", n or "")
    if d.startswith("00"):
        d = "+" + d[2:]
    digits = d.lstrip("+")
    if not d.startswith("+"):
        if len(digits) in (9, 10) and digits[0] in "03":   # numero italiano scritto senza prefisso
            digits = "39" + digits
    return "+" + digits if 8 <= len(digits) <= 15 else ""


def mask(n):
    return (n[:3] + "…" + n[-4:]) if len(n) > 8 else n


def twilio_ready():
    return bool(cfg("twilio_account_sid") and cfg("twilio_auth_token") and normalize_number(cfg("twilio_whatsapp_from").replace("whatsapp:", "")))


def vapi_ready():
    return bool(cfg("vapi_public_key") and cfg("vapi_assistant_id"))


# ---------- HTTP verso Twilio (isolato per poterlo sostituire nei test) ----------
def _twilio_request(method, path, sid, token, data=None, timeout=8):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}{path}"
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, body, method=method)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except ValueError:
            return e.code, {}
    except (urllib.error.URLError, OSError, ValueError) as e:
        return 0, {"message": f"rete non raggiungibile: {e}"}


def twilio_check():
    """Verifica le credenziali (GET account). Ritorna (ok, messaggio)."""
    sid, tok = cfg("twilio_account_sid"), cfg("twilio_auth_token")
    if not (sid and tok):
        return False, "Inserisci Account SID e Auth Token."
    st, js = _twilio_request("GET", ".json", sid, tok)
    if st == 200:
        return True, f"Credenziali valide (account {js.get('friendly_name') or sid[:6] + '…'}, stato {js.get('status', '?')})."
    return False, f"Twilio ha risposto {st}: {js.get('message', 'errore sconosciuto')}"


def _log(to, kind, ok, detail):
    try:
        ex("INSERT INTO wa_log(to_num,kind,ok,detail) VALUES(?,?,?,?)", (mask(to), kind, int(ok), str(detail)[:300]))
    except Exception:
        pass


def send_whatsapp(to, body, kind="msg"):
    """Invia un messaggio WhatsApp. Non solleva mai eccezioni: ritorna (ok, dettaglio)."""
    if not twilio_ready():
        return False, "WhatsApp/Twilio non configurato"
    num = normalize_number(to)
    if not num:
        return False, "numero non valido"
    frm = normalize_number(cfg("twilio_whatsapp_from").replace("whatsapp:", ""))
    data = {"From": "whatsapp:" + frm, "To": "whatsapp:" + num}
    text = (body or "")[:WA_LIMIT]
    if cfg("twilio_content_sid"):    # template approvato (obbligatorio per scrivere fuori dalla finestra di 24 ore)
        data["ContentSid"] = cfg("twilio_content_sid")
        # le variabili dei template WhatsApp non ammettono a capo, tabulazioni né molti spazi di fila
        flat = re.sub(r"\s*\n+\s*", " • ", text)
        data["ContentVariables"] = json.dumps({"1": re.sub(r" {2,}", " ", flat)}, ensure_ascii=False)
    else:
        data["Body"] = text
    st, js = _twilio_request("POST", "/Messages.json", cfg("twilio_account_sid"), cfg("twilio_auth_token"), data)
    ok = st in (200, 201)
    detail = (js.get("sid") or "inviato") if ok else f"{st}: {js.get('message', 'errore')}" + (f" (codice {js['code']})" if js.get("code") else "")
    _log(num, kind, ok, detail)
    return ok, detail


# ---------- destinatari ----------
def _extra_numbers():
    return [normalize_number(x) for x in re.split(r"[\n,;]+", cfg("wa_destinations")) if normalize_number(x)]


def _team_rows():
    return q("SELECT * FROM team WHERE phone != '' ORDER BY sort, id")


def recipients(kind):
    """Numeri (E.164) a cui inviare. kind: 'duty' (riepiloghi/emergenze) oppure 'report:daily|weekly|monthly'."""
    team = [m for m in _team_rows() if (m["notify"] or "si") != "no"]
    if kind == "duty":
        pick = [m for m in team if m["on_duty"] == "si"] or team
    else:
        raw = get_setting(f"report_{kind.split(':')[1]}_to", "")
        ids = {int(x) for x in raw.split(",") if x.strip().isdigit()} if raw else None
        pick = [m for m in team if ids is None or m["id"] in ids]
    out = []
    for n in [normalize_number(m["phone"]) for m in pick] + _extra_numbers():
        if n and n not in out:
            out.append(n)
    return out


def send_many(numbers, body, kind="msg"):
    res = dict(configured=twilio_ready(), recipients=len(numbers), sent=0, failed=0, errors=[])
    if not res["configured"]:
        return res
    for n in numbers:
        ok, detail = send_whatsapp(n, body, kind)
        res["sent" if ok else "failed"] += 1
        if not ok:
            res["errors"].append(f"{mask(n)}: {detail}")
    return res


def notify_duty(body, kind="duty"):
    return send_many(recipients("duty"), body, kind)


def fire(body, kind="duty", numbers=None):
    """Invio in background (non rallenta la risposta al cliente)."""
    from flask import current_app
    app = current_app._get_current_object()

    def run():
        with app.app_context():
            try:
                send_many(numbers if numbers is not None else recipients("duty"), body, kind)
            except Exception:
                pass
    threading.Thread(target=run, daemon=True).start()


# ---------- limite di richieste per chi usa gli endpoint pubblici che inviano messaggi ----------
_hits, _lock = {}, threading.Lock()


def rate_ok(bucket, limit, window):
    now = time.time()
    with _lock:
        arr = [t for t in _hits.get(bucket, []) if now - t < window]
        if len(arr) >= limit:
            _hits[bucket] = arr
            return False
        arr.append(now)
        _hits[bucket] = arr
        return True
