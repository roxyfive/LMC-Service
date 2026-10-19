"""Test restyle form / assistente / emergenza: python -m tests.test_ui"""
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_ui_")
os.environ["ADMIN_PASSWORD"] = "TestLocale123"
from backend import create_app

app = create_app()
c = app.test_client()
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


home = c.get("/").get_data(as_text=True)
js = c.get("/static/js/site.js").get_data(as_text=True)
check("form: label vere e consenso obbligatorio", home.count("<label>") >= 8 and 'name="consent" required' in home)
check("form: servizi come chip accessibili (checkbox reali)", 'class="chip"><input type="checkbox" name="services"' in home)
check("form: pulsanti oro", 'class="btn btn-gold btn-lg" type="submit">Conferma appuntamento' in home and "Invia richiesta" in home)
check("assistente: logo LMC + badge AI + tooltip", 'id="chatBtn"' in home and "logo-3d-128.webp" in home and 'class="ai-badge"' in home and 'data-tip="Assistente LMC AI"' in home)
check("assistente: niente più testo 'Assistente' nel pulsante", ">Assistente</button>" not in home)
check("chat: header con logo e 'Assistente LMC AI'", 'class="chat-id"' in home and "<b>Assistente LMC AI</b>" in home)
check("emergenza: icona microfono + 'Parla con l’AI' e fallback tel:", 'class="mic"' in home and "Parla con l’AI" in home and 'id="sos"' in home and 'href="tel:+393661782548"' in home)
check("emergenza: JS avvia Vapi se attivo, altrimenti tel:", "startVapi(true)" in js and "location.href = sos.getAttribute('href')" in js)
import json, re
css = c.get("/static/css/site.css").get_data(as_text=True)
check("palette: bianco perlato neutro, niente avorio rosato", "--ivory:#f7f8fa" in css and "--paper:#ffffff" in css and "#f8f4ec" not in css and "#c0307a" not in css)
check("effetto: canvas di sfondo + polvere d'oro rotante, rispetta reduced-motion", 'id="pageFx"' in home and "function goldDust" in js and "const reduce" in js and "prefers-reduced-motion" in css)
check("polvere d'oro in pausa fuori vista/tab nascosta", "IntersectionObserver" in js.split("function goldDust")[1].split("(function () {")[0] and "document.hidden" in js)

# suggerimenti: automatici dai dati reali
cfg = c.get("/api/config").get_json()
sg = cfg["suggestions"]
check("suggerimenti automatici (3-4) dai dati del sito", 3 <= len(sg) <= 4 and any("Noleggio attrezzature" in x for x in sg) and any("disponibili" in x for x in sg), sg)
check("suggerimento emergenza solo se attiva", any("emergenza" in x.lower() for x in sg))
H = {"X-CSRF-Token": c.get("/api/csrf").get_json()["token"]}
def chat(q):
    return c.post("/api/chat", json={"messages": [{"role": "user", "content": q}]}, headers=H).get_json()["reply"]
check("ogni suggerimento riceve una risposta sensata", all(len(chat(x)) > 30 and "Non ho questa informazione" not in chat(x) for x in sg), [chat(x)[:60] for x in sg])
check("risposta emergenza reale", "Emergenza 24h" in chat("Come funziona l'emergenza 24h?") and "+39 366 178 2548" in chat("Come funziona l'emergenza 24h?"))
check("'Sei libero a giugno?' porta alla prenotazione", "Prossimi orari liberi" in chat("Sei libero a giugno?"))
# override da Admin
lg = c.get("/admin/login").get_data(as_text=True)
tk = re.search(r'name="csrf" (?:content|value)="([0-9a-f]+)"', lg).group(1)
c.post("/admin/login", data={"csrf": tk, "username": "admin", "password": "TestLocale123"})
page = c.get("/admin/testi").get_data(as_text=True)
check("campo suggerimenti in Admin › Testi", 'name="chat_suggerimenti"' in page)
tk = re.search(r'name="csrf" (?:content|value)="([0-9a-f]+)"', page).group(1)
form = {k: v for k, v in re.findall(r'name="([a-z_0-9]+)"[^>]*value="([^"]*)"', page)}
form.update({"csrf": tk, "chat_suggerimenti": "Quanto costa un impianto audio?\nSei libero a giugno?\nCosa include il noleggio ledwall?"})
c.post("/admin/testi", data=form)
check("suggerimenti scritti in Admin hanno la precedenza", c.get("/api/config").get_json()["suggestions"] == ["Quanto costa un impianto audio?", "Sei libero a giugno?", "Cosa include il noleggio ledwall?"])
# chip e voce nel front-end
check("chip: toccabili, spariscono scrivendo", "function renderSug" in js and "inp.addEventListener('input'" in js and "hideSug()" in js and 'id="chatSug"' in home)
check("voce: microfono sempre visibile + onde animate", 'id="mic"' in home and "mic.style.display" not in js and 'id="wave"' in home and "wave[data-state=speak]" in css)
check("voce: permessi microfono con messaggi chiari, Vapi o Web Speech", "async function ensureMic" in js and "NotAllowed" in js and "c.vapi && c.vapi.enabled) vapiBtn.click(); else voiceBtn.click()" in js)
check("voce: trascrizione live e scelta miglior voce italiana", "interimResults = true" in js and "const voiceScore" in js and "speechSynthesis" in js)
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
