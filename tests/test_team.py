"""Test team/contatti/assistente: python -m tests.test_team"""
import os
import re
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_team_")
os.environ["ADMIN_PASSWORD"] = "TestLocale123"
from backend import create_app

app = create_app()
c = app.test_client()
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


def csrf(html):
    return (re.search(r'name="csrf" content="([0-9a-f]+)"', html) or re.search(r'name="csrf" value="([0-9a-f]+)"', html)).group(1)


home = c.get("/").get_data(as_text=True)
H = {"X-CSRF-Token": csrf(home)}
check("dati reali del titolare nel sito", "+39 366 178 2548" in home and "Pasquale" in home and "Aperto 24 ore" in home)
check("nessun segnaposto [DA INSERIRE] in pagina", "[DA INSERIRE" not in home)
check("link telefono e WhatsApp", 'href="tel:+393661782548"' in home and "wa.me/393661782548" in home)


def chat(text):
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": text}]}, headers=H)
    return r.status_code, (r.get_json() or {}).get("reply", "")


for q, must in [("numero di Pasquale?", "+39 366 178 2548"), ("Qual è il telefono?", "+39 366 178 2548"), ("siete aperti 24 ore?", "Aperto 24 ore"),
                ("chi è il titolare?", "Pasquale"), ("fate noleggio attrezzature?", "Noleggio"), ("ciao", "assistente")]:
    st, rep = chat(q)
    check(f"chat: {q}", st == 200 and must.lower() in rep.lower() and "[DA" not in rep, rep)

# CSRF scaduto: l'endpoint di rinnovo restituisce un token valido
check("endpoint token csrf", len(c.get("/api/csrf").get_json()["token"]) == 32)

# admin: login e gestione team
lg = c.get("/admin/login").get_data(as_text=True)
c.post("/admin/login", data={"csrf": csrf(lg), "username": "admin", "password": "TestLocale123"})
page = c.get("/admin/m/team").get_data(as_text=True)
check("admin Team e Contatti", "Team e Contatti" in page and "Pasquale" in page)
t = csrf(page)
H = {"X-CSRF-Token": c.get("/api/csrf").get_json()["token"]}   # il login rinnova la sessione
r = c.post("/admin/m/team", data={"csrf": t, "name": "Marco Rossi", "role": "Tecnico luci", "phone": "+39 333 000 1111",
                                    "email": "marco@example.com", "note": "Reperibile di sera", "visible": "si", "sort": "1"})
check("aggiunta collaboratore", r.status_code == 302)
home = c.get("/").get_data(as_text=True)
check("collaboratore sul sito", "Marco Rossi" in home and "Tecnico luci" in home and "+39 333 000 1111" in home)
st, rep = chat("numero di Marco?")
check("assistente conosce il nuovo collaboratore", "+39 333 000 1111" in rep, rep)
st, rep = chat("quali sono i contatti?")
check("assistente elenca tutto il team", "Pasquale" in rep and "Marco" in rep, rep)
rows = re.findall(r'/admin/m/team/(\d+)"', c.get("/admin/m/team").get_data(as_text=True))
mid = rows[-1]
r = c.post(f"/admin/m/team/{mid}", data={"csrf": t, "name": "Marco Rossi", "role": "Tecnico luci", "phone": "+39 333 000 1111",
                                          "email": "", "note": "", "visible": "no", "sort": "1"})
check("nascondi collaboratore", "Marco Rossi" not in c.get("/").get_data(as_text=True))
check("nascosto anche all'assistente", "Marco" not in chat("numero di Marco?")[1])
r = c.post(f"/admin/m/team/{mid}/elimina", data={"csrf": t})
check("elimina collaboratore", r.status_code == 302 and "Marco Rossi" not in c.get("/admin/m/team").get_data(as_text=True))
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
