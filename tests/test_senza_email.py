"""Sito senza email attive (SMTP non configurato, scelta del titolare): python -m tests.test_senza_email
Il sito non deve promettere email che non partono; l'email diventa facoltativa; il link per gestire la richiesta si mostra a schermo."""
import os
import re
import tempfile
import threading
from datetime import date, timedelta

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_noemail_")
os.environ["ADMIN_PASSWORD"] = "TestLocale123"
os.environ.pop("SMTP_HOST", None)
from backend import create_app

app = create_app()
c = app.test_client()
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


home = c.get("/").get_data(as_text=True)
tok = re.search(r'name="csrf" content="([0-9a-f]+)"', home).group(1)
H = {"X-CSRF-Token": tok}
check("moduli: l'email è «facoltativa» e non obbligatoria", home.count("Email (facoltativa)") == 2 and not re.search(r'name="email" type="email" required', home))
d = date.today() + timedelta(days=1)
while d.weekday() > 4:
    d += timedelta(days=1)
slots = c.get(f"/api/slots?date={d}").get_json()
body = {"name": "Mario Rossi", "phone": "3331112222", "date": str(d), "time": slots[0], "event_type": "Matrimonio", "consent": True}
r = c.post("/api/appuntamento", json=body, headers=H)
j = r.get_json()
check("prenotazione senza email: accettata", r.status_code == 200 and j["ok"], r.get_data(as_text=True))
check("prenotazione senza SMTP: mail=False e il link per gestirla è nella risposta", j["mail"] is False and "/appuntamento/" in j["link"])
check("pagina «gestisci la richiesta» raggiungibile dal link", c.get(j["link"].replace("http://localhost", "")).status_code == 200)
check("preventivo senza email: accettato", c.post("/api/preventivo", json={"name": "A B", "phone": "3331112222", "event_type": "Festa", "consent": True}, headers=H).status_code == 200)
check("email scritta male: rifiutata anche se facoltativa", c.post("/api/preventivo", json={"name": "A B", "phone": "3331112222", "email": "x", "consent": True}, headers=H).status_code == 400)
check("il pannello mostra la richiesta nuova", "Mario Rossi" in (lambda a: (a.post("/admin/login", data={"csrf": re.search(r'name="csrf" value="([0-9a-f]+)"', a.get("/admin/login").get_data(as_text=True)).group(1), "username": "admin", "password": "TestLocale123"}), a.get("/admin/").get_data(as_text=True))[1])(app.test_client()))

# con SMTP configurato l'email torna obbligatoria e il messaggio promette l'email
os.environ["SMTP_HOST"] = "smtp.example.invalid"
home2 = c.get("/").get_data(as_text=True)
check("con SMTP attivo: email obbligatoria nei moduli", re.search(r'name="email" type="email" required', home2) and "(facoltativa)" not in home2)
check("con SMTP attivo: senza email prenotazione rifiutata", c.post("/api/appuntamento", json={**body, "time": slots[1]}, headers=H).status_code == 400)
os.environ.pop("SMTP_HOST")

try:
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    srv = make_server("127.0.0.1", 0, app)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 1100, "height": 900})
        pg.goto(f"http://127.0.0.1:{srv.server_port}/?nointro=1")
        pg.wait_for_timeout(800)
        pg.fill("#bookForm [name=name]", "Anna Verdi")
        pg.fill("#bookForm [name=phone]", "3331112222")
        giorno = d + timedelta(days=1)
        while giorno.weekday() > 4:
            giorno += timedelta(days=1)
        pg.fill("#bookForm [name=date]", str(giorno))
        pg.dispatch_event("#bookForm [name=date]", "change")
        pg.wait_for_function("document.querySelector('#bookForm [name=time]').options.length > 1")
        pg.select_option("#bookForm [name=time]", index=1)
        pg.check("#bookForm [name=consent]")
        pg.click("#bookForm button[type=submit]")
        pg.wait_for_selector("#bookForm .msg.ok")
        testo = pg.inner_text("#bookForm .msg")
        check("a schermo: nessuna promessa di email, messaggio «ti contatteremo noi»", "Ti contatteremo noi" in testo and "Controlla l'email" not in testo, testo)
        check("a schermo: compare il link per gestire la richiesta", pg.query_selector("#bookForm .msg a[href*='/appuntamento/']") is not None)
        br.close()
except Exception as e:
    print("SKIP controllo a schermo:", str(e)[:80])
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
