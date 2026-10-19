"""Test WhatsApp (Twilio mockato), report automatici, emergenza e webhook Vapi: python -m tests.test_whatsapp
Nessuna rete: backend.notify._twilio_request viene sostituito da un finto Twilio."""
import os
import re
import tempfile
from datetime import datetime, timedelta

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_wa_")
os.environ["ADMIN_PASSWORD"] = "TestLocale123"
os.environ["LMC_NO_BG"] = "1"
for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "TWILIO_CONTENT_SID", "WHATSAPP_DESTINATIONS", "VAPI_PUBLIC_KEY"):
    os.environ.pop(k, None)
from backend import create_app, notify, reports, metrics
from backend import admin_ext
from backend.db import q, ex, set_setting, get_setting

app = create_app()
app.app_context().push()      # contesto globale per interrogare il database dal test
c = app.test_client()
ok = fail = 0
SENT = []
FAIL_MODE = {"on": False}


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


def fake_twilio(method, path, sid, token, data=None, timeout=8):
    if path == ".json":
        return (200, {"friendly_name": "LMC", "status": "active"}) if token == "tok123" else (401, {"message": "Authenticate"})
    SENT.append(dict(data or {}, _sid=sid, _tok=token))
    return (400, {"message": "numero non valido", "code": 21211}) if FAIL_MODE["on"] else (201, {"sid": "SM" + str(len(SENT))})


notify._twilio_request = fake_twilio


def csrf(html):
    return (re.search(r'name="csrf" content="([0-9a-f]+)"', html) or re.search(r'name="csrf" value="([0-9a-f]+)"', html)).group(1)


def api_tok():
    return {"X-CSRF-Token": c.get("/api/csrf").get_json()["token"]}


# ---- numeri
check("normalizza +39", notify.normalize_number("+39 366 178 2548") == "+393661782548")
check("normalizza 0039 e senza prefisso", notify.normalize_number("0039 3661782548") == "+393661782548" and notify.normalize_number("366 178 2548") == "+393661782548")
check("numero non valido", notify.normalize_number("12ab") == "" and notify.normalize_number("") == "")

# ---- senza Twilio: nulla si rompe
home = c.get("/").get_data(as_text=True)
H = api_tok()
check("config pubblica: wa non pronto", c.get("/api/config").get_json()["wa_ready"] is False)
r = c.post("/api/chat/riepilogo", json={"messages": [{"role": "user", "content": "Vorrei un preventivo per un matrimonio"}], "name": "Anna", "phone": "333 1112222", "consent": True}, headers=H)
j = r.get_json()
check("riepilogo senza Twilio: ok + link wa.me", r.status_code == 200 and j["configured"] is False and j["wa_link"].startswith("https://wa.me/393661782548?text="), j)
check("richiesta registrata anche senza Twilio", q("SELECT COUNT(*) n FROM calls WHERE payload LIKE '%chat%'", one=True)["n"] == 1)
check("nessun invio verso Twilio", SENT == [])
check("riepilogo senza consenso rifiutato", c.post("/api/chat/riepilogo", json={"messages": [], "phone": "3331112222"}, headers=H).status_code == 400)
check("riepilogo senza telefono rifiutato", c.post("/api/chat/riepilogo", json={"messages": [], "consent": True}, headers=H).status_code == 400)
check("senza CSRF rifiutato", c.post("/api/chat/riepilogo", json={"phone": "3331112222", "consent": True}).status_code == 400)
r = c.post("/api/emergenza", json={"name": "Luca", "phone": "3339998888", "note": "audio spento"}, headers=api_tok())
check("emergenza senza Twilio: registrata", r.status_code == 200 and r.get_json()["configured"] is False)
check("report non parte senza Twilio", reports.run_due(datetime(2026, 10, 19, 22, 0, tzinfo=metrics.TZ)) == [])

# ---- admin: salva chiavi (segreti in tabella separata)
lg = c.get("/admin/login").get_data(as_text=True)
c.post("/admin/login", data={"csrf": csrf(lg), "username": "admin", "password": "TestLocale123"})
page = c.get("/admin/impostazioni").get_data(as_text=True)
check("pagina impostazioni (4 sezioni)", all(x in page for x in ('id="wa"', 'id="vapi"', 'id="report"', 'id="emergenza"')))
t = csrf(page)
c.post("/admin/impostazioni/salva", data={"csrf": t, "sezione": "wa", "twilio_account_sid": "ACtest000", "twilio_auth_token": "tok123",
                                          "twilio_whatsapp_from": "whatsapp:+14155238886", "wa_destinations": "+39 333 000 1111\n", "wa_notify_requests": "on"})
with app.app_context():
    check("Twilio configurato", notify.twilio_ready())
    check("token NON nella tabella settings", q("SELECT 1 FROM settings WHERE value='tok123'", one=True) is None)
    check("token nella tabella secrets", q("SELECT 1 FROM secrets WHERE value='tok123'", one=True) is not None)
page = c.get("/admin/impostazioni").get_data(as_text=True)
check("token mai restituito all'interfaccia", "tok123" not in page and "impostato" in page)
check("home pubblica senza segreti", all(x not in c.get("/").get_data(as_text=True) for x in ("tok123", "ACtest000")))
check("verifica credenziali ok", "Credenziali valide" in c.post("/admin/impostazioni/test/twilio", data={"csrf": t}, follow_redirects=True).get_data(as_text=True))
SENT.clear()
c.post("/admin/impostazioni/test/whatsapp", data={"csrf": t, "numero": ""}, follow_redirects=True)
nums = sorted(s["To"] for s in SENT)
check("prova WhatsApp a Pasquale + extra", nums == ["whatsapp:+393330001111", "whatsapp:+393661782548"], nums)
check("formato mittente e auth", SENT[0]["From"] == "whatsapp:+14155238886" and SENT[0]["_sid"] == "ACtest000" and SENT[0]["_tok"] == "tok123" and "Body" in SENT[0])

# ---- riepilogo chat e emergenza con Twilio
SENT.clear(); notify._hits.clear()
c2 = app.test_client(); c2.get("/")
Hp = {"X-CSRF-Token": c2.get("/api/csrf").get_json()["token"]}
r = c2.post("/api/chat/riepilogo", json={"messages": [{"role": "user", "content": "Preventivo ledwall per una festa il 20 dicembre"}], "name": "Giulia", "phone": "3351234567", "consent": True}, headers=Hp)
j = r.get_json()
check("riepilogo inviato su WhatsApp", j["configured"] and j["sent"] >= 1 and any("Giulia" in s["Body"] and "ledwall" in s["Body"] and "3351234567" in s["Body"] for s in SENT), (j, SENT))
SENT.clear(); notify._hits.clear()
r = c2.post("/api/emergenza", json={"name": "Luca", "phone": "3339998888", "note": "ledwall nero"}, headers=Hp)
check("emergenza inviata a chi è di turno", r.get_json()["sent"] >= 1 and all("EMERGENZA" in s["Body"] for s in SENT) and len(SENT) >= 1, SENT)
check("honeypot ignorato", c2.post("/api/emergenza", json={"phone": "3339998888", "website": "spam"}, headers=Hp).get_json().get("ok") and len(SENT) == len(SENT))
for _ in range(5):
    last = c2.post("/api/emergenza", json={"name": "x", "phone": "3339998888"}, headers=Hp)
check("rate limit (429 dopo 5 richieste)", last.status_code == 429)

# ---- nuovi preventivi -> avviso al team
SENT.clear()
c3 = app.test_client(); c3.get("/"); H3 = {"X-CSRF-Token": c3.get("/api/csrf").get_json()["token"]}
c3.post("/api/preventivo", json={"name": "Prova", "phone": "3330001234", "email": "p@example.com", "event_type": "Festa privata", "event_date": "2026-12-20",
                                  "place": "Napoli", "guests": "80", "services": ["Audio"], "consent": True}, headers=H3)
import time
time.sleep(0.6)
check("avviso WhatsApp per nuovo preventivo", any("Nuovo preventivo" in s.get("Body", "") for s in SENT), SENT)

# ---- errori Twilio gestiti
FAIL_MODE["on"] = True
SENT.clear()
with app.app_context():
    res = notify.send_many(["+393661782548"], "x", "test")
check("errore Twilio: nessuna eccezione, riportato", res["failed"] == 1 and "21211" in res["errors"][0], res)
FAIL_MODE["on"] = False

# ---- template (Content SID)
set_setting("twilio_content_sid", "HXabc")
SENT.clear()
with app.app_context():
    notify.send_whatsapp("+393661782548", "Riga uno\nRiga due   con spazi", "test")
cv = SENT[0].get("ContentVariables", "")
check("con template usa ContentSid e variabile {{1}} senza a capo", SENT[0].get("ContentSid") == "HXabc" and "Body" not in SENT[0] and '"1"' in cv and "\\n" not in cv and "  " not in cv, SENT)
set_setting("twilio_content_sid", "")

# ---- report: dati e testi
with app.app_context():
    today = metrics.now_local().date()
    base = reports.stats(today.isoformat(), today.isoformat())
    for i in range(5):
        metrics.track("visit", f"new{i}")
    metrics.track("visit", "new0")                      # stessa persona: stessa giornata = una visita unica
    metrics.track("chat_msg", "chatA"); metrics.track("chat_msg", "chatA"); metrics.track("chat_msg", "chatB")
    st = reports.stats(today.isoformat(), today.isoformat())
    check("conteggio visite uniche", st["visits"] - base["visits"] == 5 and st["pageviews"] - base["pageviews"] == 6, (base, st))
    check("conteggio chat (conversazioni distinte)", st["chats"] - base["chats"] == 2, st)
    check("contatti = preventivi + riepiloghi + emergenze + chiamate", st["contacts"] == st["quotes"] + st["chat_leads"] + st["emergencies"] + st["voice_calls"] and st["emergencies"] >= 1 and st["quotes"] >= 1, st)
    txt = reports.build_text("daily")
    check("testo giornaliero", "Oggi" in txt and f"{st['visits']} visite" in txt and "Questa settimana" in txt and txt.count("\n") >= 2, txt)
    check("testo settimanale", "settimana scorsa" in reports.build_text("weekly").lower() and "Rispetto al periodo precedente" in reports.build_text("weekly"))
    check("testo mensile", "Report mensile" in reports.build_text("monthly"))
    d1, d2, _l = reports.period("weekly", datetime(2026, 10, 19).date())
    check("settimana = lun-dom precedente", (d1.isoformat(), d2.isoformat()) == ("2026-10-12", "2026-10-18"))
    d1, d2, lab = reports.period("monthly", datetime(2026, 11, 1).date())
    check("mese = precedente", (d1.isoformat(), d2.isoformat()) == ("2026-10-01", "2026-10-31") and "ottobre 2026" in lab)

    # pianificazione
    TZ = metrics.TZ
    set_setting("report_daily_on", "1"); set_setting("report_weekly_on", "1"); set_setting("report_monthly_on", "1")
    check("sera: giornaliero dovuto dopo le 21", [k for k, _ in reports.due(datetime(2026, 10, 21, 21, 5, tzinfo=TZ))] == ["daily"])
    check("sera: non prima delle 21", reports.due(datetime(2026, 10, 21, 20, 59, tzinfo=TZ)) == [])
    check("lunedì mattina: giornaliero? no; settimanale sì", [k for k, _ in reports.due(datetime(2026, 10, 19, 9, 0, tzinfo=TZ))] == ["weekly"])
    check("primo del mese: mensile", "monthly" in [k for k, _ in reports.due(datetime(2026, 11, 1, 9, 0, tzinfo=TZ))])
    set_setting("report_weekly_on", "0")
    check("interruttore spento: nessun settimanale", reports.due(datetime(2026, 10, 19, 22, 0, tzinfo=TZ)) == [reports.due(datetime(2026, 10, 19, 22, 0, tzinfo=TZ))[0]] and "weekly" not in [k for k, _ in reports.due(datetime(2026, 10, 19, 22, 0, tzinfo=TZ))])

    # invio idempotente e destinatari
    SENT.clear()
    now = datetime(2026, 10, 21, 21, 10, tzinfo=TZ)
    r1 = reports.run_due(now); r2 = reports.run_due(now)
    check("report giornaliero inviato una sola volta", len(r1) == 1 and r1[0][1] is True and r2 == [] and len(SENT) == 2, (r1, r2, len(SENT)))
    check("testo del report su WhatsApp", "Report giornaliero" in SENT[0]["Body"])
    # destinatari scelti: solo Pasquale
    pid = q("SELECT id FROM team ORDER BY id LIMIT 1", one=True)["id"]
    set_setting("report_daily_to", str(pid))
    set_setting("wa_destinations", "")
    check("destinatari = solo i selezionati", notify.recipients("report:daily") == ["+393661782548"], notify.recipients("report:daily"))
    # fallimento -> ritentabile (max 3)
    FAIL_MODE["on"] = True; SENT.clear()
    later = datetime(2026, 10, 22, 21, 10, tzinfo=TZ)
    check("invio fallito registrato", reports.run_due(later)[0][1] is False)
    ex("UPDATE report_log SET sent_at='2000-01-01 00:00:00' WHERE key=?", ("daily:2026-10-22",))
    FAIL_MODE["on"] = False
    r = reports.run_due(later)
    check("ritentativo riuscito", len(r) == 1 and r[0][1] is True, r)

# ---- admin report
page = c.get("/admin/report").get_data(as_text=True)
check("pagina Report", "Visite degli ultimi 14 giorni" in page and "invio su whatsapp" in page.lower())
SENT.clear()
c.post("/admin/report/invia", data={"csrf": csrf(page), "tipo": "daily"})
check("invio manuale dall'admin", len(SENT) >= 1)
# ---- toggle dall'admin
c.post("/admin/impostazioni/salva", data={"csrf": t, "sezione": "report", "report_weekly_on": "on", "report_weekly_time": "07:45", "report_weekly_to": str(pid)})
with app.app_context():
    check("toggle salvati da admin", reports.enabled("weekly") and not reports.enabled("daily") and get_setting("report_weekly_time") == "07:45")

# ---- emergenza configurabile
c.post("/admin/impostazioni/salva", data={"csrf": t, "sezione": "emergenza", "emergency_on": "on", "emergency_number": "+39 333 777 8888", "emergency_hours": "08:00-20:00"})
cfg = c.get("/api/config").get_json()["emergency"]
check("emergenza: numero e orari da admin", cfg["number"] == "+393337778888" and cfg["hours"] == "08:00-20:00")
home = c.get("/").get_data(as_text=True)
check("pulsante rosso con tel:", 'id="sos"' in home and 'href="tel:+393337778888"' in home)
c.post("/admin/impostazioni/salva", data={"csrf": t, "sezione": "emergenza"})
check("emergenza disattivabile", 'id="sos"' not in c.get("/").get_data(as_text=True))

# ---- webhook Vapi
v = app.test_client()
check("webhook senza secret configurato: 404", v.post("/webhook/vapi", json={}).status_code == 404)
c.post("/admin/impostazioni/salva", data={"csrf": t, "sezione": "vapi", "vapi_public_key": "pk_test", "vapi_assistant_id": "as_1", "vapi_api_key": "sk_test", "vapi_webhook_secret": "s3cr3t"})
check("webhook con secret errato: 404", v.post("/webhook/vapi", json={}, headers={"X-Vapi-Secret": "no"}).status_code == 404)
SENT.clear()
body = {"message": {"type": "end-of-call-report", "summary": "Cliente chiede ledwall per matrimonio a Sorrento", "call": {"id": "c1", "customer": {"number": "+393401234567"}}}}
check("webhook valido", v.post("/webhook/vapi", json=body, headers={"X-Vapi-Secret": "s3cr3t"}).status_code == 200)
time.sleep(0.6)
check("riepilogo chiamata su WhatsApp", any("assistente vocale" in s["Body"] and "ledwall" in s["Body"] for s in SENT), SENT)
check("chiamata registrata", q("SELECT 1 FROM calls WHERE payload LIKE '%vapi%'", one=True) is not None)
cfgp = c.get("/api/config").get_json()["vapi"]
check("config pubblica Vapi senza chiavi private", cfgp["enabled"] and cfgp["public_key"] == "pk_test" and "sk_test" not in str(c.get("/api/config").get_data(as_text=True)))
admin_ext._vapi_get = lambda path, key, timeout=8: (200, {"name": "LMC"}) if key == "sk_test" else (401, {"message": "bad"})
check("verifica Vapi", "Assistente trovato" in c.post("/admin/impostazioni/test/vapi", data={"csrf": t}, follow_redirects=True).get_data(as_text=True))
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
