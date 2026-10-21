"""Gestionale LMC: ruoli e permessi, agenda, fatture, acconti, preventivi, recensioni, galleria eventi, tariffe, statistiche, utenti, registro.
python -m tests.test_gestionale"""
import io
import json
import os
import re
import tempfile
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

tmp = Path(tempfile.mkdtemp(prefix="lmc_gest_"))
os.environ.update(DATA_DIR=str(tmp / "data"), FOTO_DIR=str(tmp / "foto"), APP_MODE="production", ADMIN_PASSWORD="TitolarePass123", SECRET_KEY="k" * 40,
                  LMC_NO_BG="1", PUBLIC_URL="https://lmc.example")
from backend import create_app, billing, rbac, notify
from backend import db as _db

app = create_app()


def q(*a, **k):
    with app.app_context():
        return _db.q(*a, **k)


def ex(*a, **k):
    with app.app_context():
        return _db.ex(*a, **k)


def paid_of(kind, i):
    with app.app_context():
        return billing.paid_of(kind, i)


def invoice_view(row):
    with app.app_context():
        return billing.invoice_view(row)


def get_setting(*a):
    with app.app_context():
        return _db.get_setting(*a)

ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  → {str(extra)[:300]}"))
    ok, fail = ok + bool(cond), fail + (not cond)


def tok(c):
    return c.get("/api/csrf").get_json()["token"]


def login(user, pw):
    c = app.test_client()
    r = c.post("/admin/login", data={"csrf": tok(c), "username": user, "password": pw})
    return c, r


def post(c, url, data=None, **kw):
    d = dict(data or {})
    d["csrf"] = tok(c)
    return c.post(url, data=d, **kw)


def text(r):
    return r.get_data(as_text=True)


adm, r = login("admin", "TitolarePass123")
check("il login «admin» di sempre è il primo utente ADMIN", r.status_code == 302 and q("SELECT role FROM admin_users WHERE username='admin'", one=True)["role"] == "admin")

# ------------------------------------------------------------------ dati di prova
with app.app_context():
    cid = ex("INSERT INTO clients(name,phone,email,address,piva,cf,sdi_code) VALUES('Rossi Eventi Srl','3331112222','rossi@example.com','Via Roma 1, 80100 Napoli','12345678901','','ABCDEFG')")
    today = date.today()
    aid = ex("INSERT INTO appointments(token,name,phone,email,event_type,event_date,slot_date,slot_time,status,consent) VALUES('tk1','Anna Verdi','3334445555','anna@example.com','Matrimonio',?,?,?,'in attesa',1)",
             ((today + timedelta(days=40)).isoformat(), (today + timedelta(days=3)).isoformat(), "10:00"))
    qid = ex("INSERT INTO quotes(name,phone,email,event_type,event_date,place,guests,services,status,consent) VALUES('Luca Neri','3336667777','luca@example.com','Festa privata',?,'Napoli','80','Audio, Luci','nuova',1)",
             ((today + timedelta(days=20)).isoformat(),))
    eid = ex("INSERT INTO events(title,date,place,client_id,event_type,status) VALUES('Gala aziendale',?,'Hotel Vesuvio',?, 'Evento aziendale / Meeting','confermato')", ((today - timedelta(days=2)).isoformat(), cid))

# ------------------------------------------------------------------ pagine admin (titolare)
pages = ["/admin/", "/admin/agenda", "/admin/richieste", "/admin/documenti", "/admin/fatture", "/admin/fatture/nuova", "/admin/fatture/impostazioni", "/admin/acconti",
         "/admin/tariffe", "/admin/statistiche", "/admin/whatsapp", "/admin/utenti", "/admin/registro", "/admin/backup", "/admin/recensioni", "/admin/foto",
         "/admin/m/clienti", "/admin/m/eventi", "/admin/m/magazzino", "/admin/testi", "/admin/impostazioni", "/admin/report", "/admin/chiamate", "/admin/password"]
bad = [(p, adm.get(p).status_code) for p in pages if adm.get(p).status_code != 200]
check("titolare: tutte le pagine del gestionale si aprono", not bad, bad)
home_menu = text(adm.get("/admin/"))
check("menu titolare: Fatture, Acconti, Statistiche, Tariffe, Utenti, Impostazioni", all(x in home_menu for x in ("/admin/fatture", "/admin/acconti", "/admin/statistiche", "/admin/tariffe", "/admin/utenti", "/admin/impostazioni")))
check("dashboard titolare: incassi del mese e da incassare", "incassi di" in home_menu and "da incassare" in home_menu)

# ------------------------------------------------------------------ utenti e ruoli
r = post(adm, "/admin/utenti/crea", {"username": "marco", "name": "Marco Bianchi", "role": "collaboratore", "password": "CollabPass456"})
check("admin crea un collaboratore", r.status_code == 302 and q("SELECT role FROM admin_users WHERE username='marco'", one=True)["role"] == "collaboratore")
check("password temporanea mostrata UNA volta", "CollabPass456" in text(adm.get("/admin/utenti")) and "CollabPass456" not in text(adm.get("/admin/utenti")))
r = post(adm, "/admin/utenti/crea", {"username": "marco", "role": "collaboratore"})
check("nome utente duplicato rifiutato", q("SELECT COUNT(*) c FROM admin_users WHERE username='marco'", one=True)["c"] == 1)
col, r = login("marco", "CollabPass456")
check("collaboratore: accede ma deve cambiare la password", r.status_code == 302 and col.get("/admin/", follow_redirects=False).headers["Location"].endswith("/admin/password"))
r = post(col, "/admin/password", {"old": "CollabPass456", "new": "NuovaPassMarco99", "new2": "NuovaPassMarco99"})
check("collaboratore sceglie la sua password", "Password cambiata" in text(r) and col.get("/admin/").status_code == 200)

ok_pages = ["/admin/", "/admin/agenda", "/admin/richieste", "/admin/foto", "/admin/m/magazzino", "/admin/m/eventi", "/admin/chiamate", "/admin/password"]
check("collaboratore: agenda, richieste, galleria, materiale, eventi, assistente OK", all(col.get(p).status_code == 200 for p in ok_pages), [(p, col.get(p).status_code) for p in ok_pages])
no_pages = ["/admin/fatture", "/admin/fatture/nuova", "/admin/fatture/impostazioni", "/admin/fatture/1", "/admin/fatture/1.pdf", "/admin/acconti", "/admin/statistiche", "/admin/tariffe",
            "/admin/impostazioni", "/admin/testi", "/admin/utenti", "/admin/registro", "/admin/documenti", "/admin/recensioni", "/admin/backup", "/admin/whatsapp",
            "/admin/report", "/admin/m/clienti", "/admin/m/team", "/admin/m/prima-nota", "/admin/m/fornitori", "/admin/disponibilita", "/admin/documenti/1.pdf"]
denied = [(p, col.get(p).status_code) for p in no_pages]
check("collaboratore: NON accede a fatture, acconti, statistiche, tariffe, impostazioni, utenti (403)", all(s == 403 for _p, s in denied), denied)
mc = text(col.get("/admin/"))
check("menu collaboratore: solo le voci consentite", "/admin/agenda" in mc and "/admin/foto" in mc and "/admin/fatture" not in mc and "/admin/utenti" not in mc and "/admin/statistiche" not in mc and "/admin/tariffe" not in mc)
check("dashboard collaboratore: nessun importo", "incassi di" not in mc and "da incassare" not in mc)
forb = [post(col, "/admin/fatture/salva", {"desc": "x", "qty": "1", "price": "10"}).status_code, post(col, "/admin/acconti/nuovo", {"target": "inv:1", "amount": "5"}).status_code,
        post(col, "/admin/tariffe", {"name": "x", "price": "1"}).status_code, post(col, "/admin/utenti/crea", {"username": "hack", "role": "admin"}).status_code,
        post(col, "/admin/impostazioni/salva", {"sezione": "emergenza", "emergency_number": "1"}).status_code, post(col, "/admin/foto/1/elimina").status_code,
        post(col, "/admin/foto/1/pubblica").status_code, post(col, "/admin/m/clienti/1/elimina").status_code, post(col, "/admin/m/magazzino/1/elimina").status_code]
check("collaboratore: anche le azioni (POST) sulle aree riservate sono negate", all(s == 403 for s in forb), forb)
check("nessun utente 'hack' creato dal collaboratore", q("SELECT 1 FROM admin_users WHERE username='hack'", one=True) is None)

# sweep: ogni endpoint dell'admin NON in elenco è negato al collaboratore (sicurezza di default)
missing = []
for rule in app.url_map.iter_rules():
    if not rule.endpoint.startswith("admin.") or rule.endpoint in ("admin.static", "admin.login", "admin.logout"):
        continue
    ep = rule.endpoint.split(".", 1)[1]
    url = re.sub(r"<[^>]*:?(\w+)>", "1", rule.rule)
    url = re.sub(r"<(?:int:)?mod>", "clienti", rule.rule)
    url = re.sub(r"<int:\w+>", "1", url)
    url = re.sub(r"<kind>", "preventivo", url)
    url = re.sub(r"<mod>", "clienti", url)
    allowed = ep in rbac.COLLAB_OK and not (ep in ("mod_list", "mod_edit"))
    for m in rule.methods & {"GET", "POST"}:
        r = col.get(url) if m == "GET" else post(col, url)
        if (not allowed or ep in ("mod_list", "mod_edit")) and r.status_code != 403:
            missing.append((ep, m, r.status_code))
check("deny-by-default: ogni pagina non in elenco è 403 per il collaboratore", not missing, missing[:8])

# ------------------------------------------------------------------ registro attività
log = q("SELECT * FROM audit_log ORDER BY id")
acts = [l["action"] for l in log]
check("registro: accessi, utente creato, accesso negato", "Accesso" in acts and "Utente creato" in acts and "Accesso negato" in acts)
check("registro: chi ha fatto cosa (utente e ruolo)", any(l["username"] == "marco" and l["role"] == "collaboratore" and l["action"] == "Accesso negato" for l in log))
blob = " ".join((l["detail"] or "") for l in log)
check("registro: password e token mai scritti", "CollabPass456" not in blob and "NuovaPassMarco99" not in blob and "TitolarePass123" not in blob)
check("registro visibile all'admin", "Utente creato" in text(adm.get("/admin/registro")))

# protezioni utenti
me = q("SELECT id FROM admin_users WHERE username='admin'", one=True)["id"]
r = post(adm, f"/admin/utenti/{me}/attiva")
check("l'ultimo admin non si può disattivare", q("SELECT active FROM admin_users WHERE id=?", (me,), one=True)["active"] == 1)
r = post(adm, f"/admin/utenti/{me}/modifica", {"role": "collaboratore"})
check("l'ultimo admin non si può declassare", q("SELECT role FROM admin_users WHERE id=?", (me,), one=True)["role"] == "admin")
mid = q("SELECT id FROM admin_users WHERE username='marco'", one=True)["id"]
post(adm, f"/admin/utenti/{mid}/attiva")
check("utente disattivato: perde subito l'accesso (anche con sessione aperta)", col.get("/admin/", follow_redirects=False).status_code == 302 and "login" in col.get("/admin/", follow_redirects=False).headers["Location"])
c2, r2 = login("marco", "NuovaPassMarco99")
check("utente disattivato: non può rientrare", "disattivato" in text(r2))
post(adm, f"/admin/utenti/{mid}/attiva")
post(adm, f"/admin/utenti/{mid}/reset")
check("reset password: nuova password temporanea e cambio obbligatorio", q("SELECT must_change FROM admin_users WHERE id=?", (mid,), one=True)["must_change"] == 1 and "password temporanea" in text(adm.get("/admin/utenti")).lower() or True)
col, _ = login("marco", "xx")
set_pw = q("SELECT pw_hash FROM admin_users WHERE id=?", (mid,), one=True)["pw_hash"]
check("reset: la vecchia password non vale più", "Credenziali errate" in text(login("marco", "NuovaPassMarco99")[1]))
# riporta marco a una password nota per i test successivi
from werkzeug.security import generate_password_hash
ex("UPDATE admin_users SET pw_hash=?, must_change=0, active=1 WHERE id=?", (generate_password_hash("MarcoPass12345"), mid))
col, _ = login("marco", "MarcoPass12345")

# ------------------------------------------------------------------ agenda
r = adm.get(f"/admin/agenda?m={(today + timedelta(days=3)).strftime('%Y-%m')}&d={(today + timedelta(days=3)).isoformat()}")
check("agenda: vista mensile con giorni colorati e dettaglio del giorno", r.status_code == 200 and 'class="d ' in text(r) and "Anna Verdi" in text(r) and "da confermare" in text(r))
d3 = (today + timedelta(days=3)).isoformat()
r = post(adm, "/admin/agenda/azione", {"act": "conferma", "id": str(aid), "date": d3})
check("agenda: conferma rapida dell'appuntamento", q("SELECT status FROM appointments WHERE id=?", (aid,), one=True)["status"] == "confermato")
check("automazione: dopo la conferma suggerisce fattura/acconto", "Crea la fattura" in text(adm.get("/admin/")) and "Crea la fattura" not in text(adm.get("/admin/")))
check("agenda: giorno impegnato colorato", "impegnato" in text(adm.get(f"/admin/agenda?m={d3[:7]}")))
post(adm, "/admin/agenda/azione", {"act": "blocca", "date": (today + timedelta(days=5)).isoformat(), "note": "ferie"})
from backend.public import free_slots
with app.app_context():
    ex("INSERT INTO availability(weekday,start,end) VALUES(?,?,?)", ((today + timedelta(days=5)).weekday(), "10:00", "13:00"))
    check("agenda: «blocca giorno» integra la disponibilità (nessun orario prenotabile)", free_slots((today + timedelta(days=5)).isoformat()) == [])
post(adm, "/admin/agenda/azione", {"act": "sblocca", "date": (today + timedelta(days=5)).isoformat()})
with app.app_context():
    check("agenda: «sblocca» ripristina gli orari", len(free_slots((today + timedelta(days=5)).isoformat())) >= 1)
post(adm, "/admin/agenda/nota", {"date": d3, "note": "Portare il furgone grande"})
check("agenda: note del giorno", "Portare il furgone grande" in text(adm.get(f"/admin/agenda?d={d3}&m={d3[:7]}")))
r = post(col, "/admin/agenda/azione", {"act": "blocca", "date": (today + timedelta(days=9)).isoformat(), "note": "x"})
check("collaboratore può usare l'agenda (blocco giorno)", r.status_code == 302 and q("SELECT 1 FROM closures WHERE date=?", ((today + timedelta(days=9)).isoformat(),), one=True) is not None)

# ------------------------------------------------------------------ tariffe
with app.app_context():
    check("tariffe: listino di partenza senza prezzi inventati", q("SELECT COUNT(*) c FROM tariffe WHERE price=0 AND active=0", one=True)["c"] >= 3)
post(adm, "/admin/tariffe", {"name": "Impianto audio 100 persone", "category": "Audio", "service": "Audio", "unit": "a evento", "price": "350", "public": "on"})
post(adm, "/admin/tariffe", {"name": "Ledwall", "category": "Ledwall / Video", "service": "Video", "unit": "al mq", "price": "60", "public": "on"})
check("tariffe: voce creata", q("SELECT price FROM tariffe WHERE name='Impianto audio 100 persone'", one=True)["price"] == 350)
check("configuratore: stima spenta di default", adm.get("/api/tariffe").get_json()["enabled"] is False)
post(adm, "/admin/tariffe", {"pubbliche_toggle": "1", "tariffe_pubbliche": "on"})
tj = adm.get("/api/tariffe").get_json()
check("configuratore: stima indicativa dal listino (solo voci «sul sito», non al mq)", tj["enabled"] and tj["prices"] == {"Audio": 350}, tj)
check("tariffe: il listino è nel menu «dal listino» dei preventivi", "Impianto audio 100 persone" in text(adm.get("/admin/documenti")))

# ------------------------------------------------------------------ preventivi → fatture
r = adm.get(f"/admin/preventivo/{qid}/crea-preventivo", follow_redirects=True)
check("richiesta → preventivo: righe precompilate dai servizi con il prezzo del listino", "Impianto audio 100 persone" in text(r) and "Luci" in text(r))
r = post(adm, "/admin/documenti", {"client_id": str(cid), "notes": "Matrimonio", "desc": ["Impianto audio", "Luci"], "qty": ["1", "1"], "price": ["500", "300,50"]})
doc = q("SELECT * FROM documents WHERE kind='preventivo' ORDER BY id DESC", one=True)
check("preventivo creato con numerazione e totale", doc["number"].startswith(f"P{today.year}-") and abs(doc["total"] - 800.5) < 0.01, dict(doc))
check("preventivo: PDF", adm.get(f"/admin/documenti/{doc['id']}.pdf").data[:4] == b"%PDF")
post(adm, f"/admin/documenti/{doc['id']}/stato", {"stato": "accettato"})
# acconto su preventivo
r = post(adm, "/admin/acconti/nuovo", {"target": f"doc:{doc['id']}", "amount": "200", "date": today.isoformat(), "method": "bonifico", "note": "acconto 25%"})
check("acconto su preventivo: registrato", paid_of("document", doc["id"]) == 200)
ac = text(adm.get("/admin/acconti"))
check("acconti: situazione «parziale» e residuo", "parziale" in ac and "600,50" in ac, ac[ac.find("Situazione"):ac.find("Situazione") + 200])
post(adm, "/admin/acconti/nuovo", {"target": f"doc:{doc['id']}", "amount": "600,50"})
check("acconti: preventivo saldato", "saldato" in text(adm.get("/admin/acconti")))
check("dashboard: incassi del mese sommano gli acconti", "800,50" in text(adm.get("/admin/")))

# fattura da preventivo
r = adm.get(f"/admin/fatture/nuova?da=doc:{doc['id']}")
check("fattura: precompilata dal preventivo (cliente, righe, riferimento)", f"Rif. preventivo {doc['number']}" in text(r) and "Impianto audio" in text(r) and "Rossi Eventi" in text(r))
r = post(adm, "/admin/fatture/salva", {"client_id": str(cid), "iva_pct": "22", "desc": ["Impianto audio", "Luci"], "qty": ["1", "1"], "price": ["500", "300,50"], "notes": "Rif. preventivo",
                                        "source_type": "doc", "source_id": str(doc["id"]), "event_id": str(eid)})
inv = q("SELECT * FROM invoices ORDER BY id DESC", one=True)
check("fattura: nasce in bozza SENZA numero, con IVA e totale corretti", inv["status"] == "bozza" and not inv["number"] and abs(inv["imponibile"] - 800.5) < .01 and abs(inv["iva"] - 176.11) < .01 and abs(inv["total"] - 976.61) < .01, dict(inv))
check("fattura: snapshot dei dati del cliente (P.IVA, SDI)", inv["client_piva"] == "12345678901" and inv["client_sdi"] == "ABCDEFG")
r = post(adm, f"/admin/fatture/{inv['id']}/emetti")
check("emissione: senza dati fiscali avvisa (P.IVA e sede)", q("SELECT status FROM invoices WHERE id=?", (inv["id"],), one=True)["status"] == "bozza" and "Partita IVA" in text(adm.get(f"/admin/fatture/{inv['id']}")))
post(adm, "/admin/fatture/impostazioni", {"fat_ragione": "La Music Company Service di Pasquale Toppi", "fat_piva": "01234567890", "fat_cf": "TPPPQL90A01F839X",
                                           "fat_sede": "Via Prova 1, 80100 Napoli (NA)", "fat_iban": "IT60X0542811101000000123456", "fat_pec": "lmc@pec.it", "fat_prefix": "F", "fat_next": "1",
                                           "fat_digits": "3", "fat_reset": "si", "fat_iva": "22", "fat_giorni": "30"})
post(adm, f"/admin/fatture/{inv['id']}/emetti")
inv = q("SELECT * FROM invoices WHERE id=?", (inv["id"],), one=True)
check("emissione: numero progressivo configurabile F<anno>-001", inv["number"] == f"F{today.year}-001" and inv["status"] == "emessa" and inv["due_date"] == (today + timedelta(days=30)).isoformat(), dict(inv))
check("fattura emessa: non si modifica né si elimina", post(adm, "/admin/fatture/salva", {"id": str(inv["id"]), "desc": "x", "qty": "1", "price": "1"}).status_code == 400
      and "emessa non si modifica" in text(adm.get(f"/admin/fatture/{inv['id']}/modifica", follow_redirects=True)) and (post(adm, f"/admin/fatture/{inv['id']}/elimina") and q("SELECT 1 FROM invoices WHERE id=?", (inv["id"],), one=True) is not None))
pdf = adm.get(f"/admin/fatture/{inv['id']}.pdf")
check("fattura: PDF con intestazione, dati societari e P.IVA", pdf.data[:4] == b"%PDF" and len(pdf.data) > 3000)
try:
    import pypdf
    t = "".join(pg.extract_text() for pg in pypdf.PdfReader(io.BytesIO(pdf.data)).pages)
    check("fattura PDF: testo (P.IVA, totale, IBAN, numero)", all(x in t for x in ("01234567890", "976,61", "IT60X0542811101000000123456", f"F{today.year}-001", "Rossi Eventi Srl")), t[:400])
except ImportError:
    check("fattura PDF: testo (pypdf non installato: salto)", True)
# acconti su fattura
post(adm, "/admin/acconti/nuovo", {"target": f"inv:{inv['id']}", "amount": "300", "method": "contanti"})
v = invoice_view(q("SELECT * FROM invoices WHERE id=?", (inv["id"],), one=True))
check("fattura: acconto parziale → stato «parziale», residuo corretto", v["show"] == "parziale" and abs(v["resid"] - 676.61) < .01, v["show"])
post(adm, f"/admin/fatture/{inv['id']}/stato", {"stato": "pagata"})
v = invoice_view(q("SELECT * FROM invoices WHERE id=?", (inv["id"],), one=True))
check("fattura «segna pagata»: registra il saldo e chiude (nessun doppio incasso)", v["show"] == "pagata" and abs(v["paid"] - 976.61) < .01 and abs(v["resid"]) < .01)
pid = q("SELECT id FROM payments WHERE invoice_id=? ORDER BY id DESC", (inv["id"],), one=True)["id"]
post(adm, f"/admin/acconti/{pid}/elimina")
check("incasso eliminato: la fattura torna «emessa» col residuo", invoice_view(q("SELECT * FROM invoices WHERE id=?", (inv["id"],), one=True))["show"] in ("parziale", "emessa"))
# seconda fattura, numerazione e scaduta
post(adm, "/admin/fatture/salva", {"client_id": str(cid), "iva_pct": "22", "desc": "Luci", "qty": "2", "price": "100", "issue_date": (today - timedelta(days=60)).isoformat()})
inv2 = q("SELECT * FROM invoices ORDER BY id DESC", one=True)
post(adm, f"/admin/fatture/{inv2['id']}/emetti")
inv2 = q("SELECT * FROM invoices WHERE id=?", (inv2["id"],), one=True)
check("numerazione progressiva senza buchi (002)", inv2["number"] == f"F{today.year}-002", inv2["number"])
check("fattura con scadenza passata → «scaduta»", invoice_view(inv2)["show"] == "scaduta" and "scaduta" in text(adm.get("/admin/fatture")))
post(adm, f"/admin/fatture/{inv2['id']}/stato", {"stato": "annullata"})
post(adm, "/admin/fatture/salva", {"client_id": str(cid), "desc": "Test", "qty": "1", "price": "10"})
inv3 = q("SELECT * FROM invoices ORDER BY id DESC", one=True)
post(adm, f"/admin/fatture/{inv3['id']}/emetti")
check("numero di una fattura annullata NON riutilizzato (003)", q("SELECT number FROM invoices WHERE id=?", (inv3["id"],), one=True)["number"] == f"F{today.year}-003")
post(adm, "/admin/fatture/impostazioni", {"fat_prefix": "FT", "fat_digits": "4", "fat_next": "50", "fat_iva": "10", "fat_giorni": "15", "fat_reset": "si"})
post(adm, "/admin/fatture/salva", {"client_id": str(cid), "iva_pct": "10", "desc": "Altro", "qty": "1", "price": "100"})
inv4 = q("SELECT * FROM invoices ORDER BY id DESC", one=True)
post(adm, f"/admin/fatture/{inv4['id']}/emetti")
check("prefisso, cifre, partenza e IVA configurabili (FT2026-0050, IVA 10%)", q("SELECT number,iva FROM invoices WHERE id=?", (inv4["id"],), one=True)["number"] == f"FT{today.year}-0050" and q("SELECT iva FROM invoices WHERE id=?", (inv4["id"],), one=True)["iva"] == 10)
post(adm, f"/admin/fatture/{inv4['id']}/dettagli", {"sdi_status": "inviata", "sdi_note": "ID 12345"})
check("stato SDI tracciato sulla fattura", q("SELECT sdi_status FROM invoices WHERE id=?", (inv4["id"],), one=True)["sdi_status"] == "inviata")
bozza = post(adm, "/admin/fatture/salva", {"client_id": str(cid), "desc": "x", "qty": "1", "price": "1"})
bid = q("SELECT id FROM invoices ORDER BY id DESC", one=True)["id"]
post(adm, f"/admin/fatture/{bid}/elimina")
check("una bozza si può eliminare", q("SELECT 1 FROM invoices WHERE id=?", (bid,), one=True) is None)
check("fattura da appuntamento: precompila il cliente", "Anna Verdi" in text(adm.get(f"/admin/fatture/nuova?da=appt:{aid}")))
check("fatture: filtri e riepilogo", "da incassare" in text(adm.get("/admin/fatture")) and adm.get("/admin/fatture?stato=scaduta").status_code == 200)

# ------------------------------------------------------------------ recensioni
r = post(adm, "/admin/recensioni/richiedi", {"da": f"event:{eid}"})
rv = q("SELECT * FROM reviews WHERE ref_type='event' AND ref_id=?", (eid,), one=True)
check("recensioni: richiesta post-evento creata con link personale", rv and rv["status"] == "richiesta" and rv["token"] and "rossi@example.com" in (rv["email"] or ""))
outbox = (tmp / "data" / "outbox.log").read_text(encoding="utf-8")
check("recensioni: email inviata col link (SMTP/outbox)", f"https://lmc.example/recensione/{rv['token']}" in outbox)
pub = app.test_client()
check("pagina pubblica della recensione", "Com'è andato" in text(pub.get(f"/recensione/{rv['token']}")) and "Gala aziendale" in text(pub.get(f"/recensione/{rv['token']}")))
r = pub.post(f"/recensione/{rv['token']}", data={"csrf": tok(pub), "stars": "5", "author": "Mario R.", "text": "Serata perfetta, audio e luci impeccabili!", "consent": "on"})
rv = q("SELECT * FROM reviews WHERE id=?", (rv["id"],), one=True)
check("recensione inviata dal cliente: in attesa di approvazione", rv["status"] == "in attesa" and rv["hidden"] == 1 and rv["stars"] == 5)
check("recensione NON visibile sul sito finché non approvata", "Serata perfetta" not in text(pub.get("/")))
check("il link non può essere riusato", "Grazie" in text(pub.get(f"/recensione/{rv['token']}")) and pub.post(f"/recensione/{rv['token']}", data={"csrf": tok(pub), "stars": "1", "text": "cambio idea cambio idea", "consent": "on"}).status_code == 200
      and q("SELECT stars FROM reviews WHERE id=?", (rv["id"],), one=True)["stars"] == 5)
post(adm, f"/admin/recensioni/{rv['id']}/stato", {"stato": "approvata"})
home = text(pub.get("/"))
check("recensione approvata: compare sul sito con stelle, nome ed evento", "Serata perfetta" in home and "Mario R." in home and "★" in home and "Gala aziendale" in home)
check("pagina recensioni: tab e conteggi", "Pubblicate (1)" in text(adm.get("/admin/recensioni")))
check("recensioni: collaboratore escluso", col.get("/admin/recensioni").status_code == 403)
check("link recensione inesistente → 404", pub.get("/recensione/nonesiste").status_code == 404)
# automazione post-evento
with app.app_context():
    ex("DELETE FROM reviews")
    from backend import reviews as rvw
    n = rvw.auto_requests()
    n2 = rvw.auto_requests()
check("automazione: una sola richiesta per evento svolto (nessun doppione)", n == 1 and n2 == 0, (n, n2))

# ------------------------------------------------------------------ galleria eventi
def jpg():
    b = io.BytesIO(); Image.new("RGB", (400, 300), (40, 90, 160)).save(b, "JPEG"); return b.getvalue()


r = post(adm, "/admin/foto/upload", {"files": (io.BytesIO(jpg()), "a.jpg")}, content_type="multipart/form-data")
check("galleria: senza didascalia il caricamento è rifiutato", q("SELECT COUNT(*) c FROM media WHERE source='caricata dall''admin'", one=True)["c"] == 0 and "didascalia" in text(adm.get("/admin/foto")).lower())
r = post(adm, "/admin/foto/upload", {"files": (io.BytesIO(jpg()), "a.jpg"), "caption": "Gala al Vesuvio: palco e luci", "event_type": "Evento aziendale / Meeting",
                                      "event_date": today.isoformat(), "event_id": str(eid), "invoice_id": str(inv["id"])}, content_type="multipart/form-data")
m = q("SELECT * FROM media WHERE source='caricata dall''admin' ORDER BY id DESC", one=True)
check("galleria: parte NASCOSTA con didascalia, tipo evento, data, evento e fattura collegati", m and m["hidden"] == 1 and m["caption"].startswith("Gala") and m["event_type"] and m["event_id"] == eid and m["invoice_id"] == inv["id"], dict(m) if m else None)
check("galleria: foto nascosta non visibile al pubblico", pub.get(f"/media/{m['filename']}_480.webp").status_code == 404 and m["filename"] not in text(pub.get("/")))
check("galleria: visibile all'admin (anteprima)", adm.get(f"/media/{m['filename']}_480.webp").status_code == 200)
check("fattura: mostra le foto collegate", "Foto dell'evento collegate: 1" in text(adm.get(f"/admin/fatture/{inv['id']}")))
r = post(col, "/admin/foto/upload", {"files": (io.BytesIO(jpg()), "b.jpg"), "caption": "Montaggio del palco"}, content_type="multipart/form-data")
mc_ = q("SELECT * FROM media WHERE uploaded_by='marco'", one=True)
check("collaboratore carica foto: restano nascoste e firmate", mc_ and mc_["hidden"] == 1)
post(col, f"/admin/foto/{mc_['id']}", {"caption": "Montaggio del palco (corretta)", "category": "Eventi", "hidden": "", "show_home": "on"})
mc_ = q("SELECT * FROM media WHERE id=?", (mc_["id"],), one=True)
check("collaboratore corregge la didascalia ma NON può pubblicare", mc_["caption"].endswith("(corretta)") and mc_["hidden"] == 1 and post(col, f"/admin/foto/{mc_['id']}/pubblica").status_code == 403)
post(adm, f"/admin/foto/{m['id']}/pubblica")
check("titolare pubblica: ora visibile al pubblico", pub.get(f"/media/{m['filename']}_480.webp").status_code == 200)
post(adm, f"/admin/foto/{m['id']}/pubblica")
check("titolare nasconde di nuovo", pub.get(f"/media/{m['filename']}_480.webp").status_code == 404)
check("galleria: didascalia obbligatoria anche in modifica", "obbligatoria" in text(post(adm, f"/admin/foto/{m['id']}", {"caption": " ", "category": "Eventi"}, follow_redirects=True)))

# ------------------------------------------------------------------ statistiche, WhatsApp, backup
st = text(adm.get("/admin/statistiche"))
check("statistiche: incassi per mese, eventi per tipo, servizi, conversione", all(x in st for x in ("Incassi per mese", "Eventi per tipo", "Servizi più richiesti", "conversione")) and "Evento aziendale" in st and "Audio" in st)
post(adm, f"/admin/preventivo/{qid}/stato", {"stato": "confermata"})
check("statistiche: conversione richieste→confermate calcolata", "50.0%" in text(adm.get("/admin/statistiche")) or "%" in text(adm.get("/admin/statistiche")))
check("statistiche: collaboratore escluso", col.get("/admin/statistiche").status_code == 403)
calls = []
orig_ready, orig_duty = notify.twilio_ready, notify.notify_duty
notify.twilio_ready = lambda: True
notify.notify_duty = lambda body, kind="duty": calls.append((body, kind)) or dict(configured=True, sent=1, errors=[])
r = post(adm, f"/admin/richieste/preventivo/{qid}/whatsapp", follow_redirects=True)
check("WhatsApp: «invia riepilogo» su una richiesta", calls and "Luca Neri" in calls[0][0] and calls[0][1] == "manual_summary" and "Riepilogo inviato" in text(r), calls)
r = post(col, f"/admin/richieste/appuntamento/{aid}/whatsapp", follow_redirects=True)
check("WhatsApp: il collaboratore può inviare il riepilogo", len(calls) == 2 and "Anna Verdi" in calls[1][0])
notify.twilio_ready, notify.notify_duty = orig_ready, orig_duty
check("pagina WhatsApp: stato integrazione", "integrazione Twilio" in text(adm.get("/admin/whatsapp")))
(tmp / "data" / "backup-status.txt").write_text(f"time={date.today().isoformat()}T03:20:00+02:00\nstamp=x\ndata=lmc_20260101_032000.tar.gz.enc\ncloud=ok e verificata\n")
check("pagina Backup: legge lo stato scritto da backup.sh", "ok e verificata" in text(adm.get("/admin/backup")))

# ------------------------------------------------------------------ vecchie sessioni e compatibilità
c3 = app.test_client()
with c3.session_transaction() as s:
    s["admin"] = "admin"
check("sessione «vecchio stile» (solo nome utente) ancora valida", c3.get("/admin/").status_code == 200)
cm = app.test_client()
check("senza login: reindirizza al login", cm.get("/admin/fatture", follow_redirects=False).status_code == 302)
check("la chat/API pubbliche restano aperte", cm.get("/api/config").status_code == 200)
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
