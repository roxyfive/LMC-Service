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
check("palette: bianco puro, niente avorio/rosato/magenta", "--ivory:#ffffff" in css and "--paper:#ffffff" in css and "#f8f4ec" not in css and "#f7f8fa" not in css and "#c0307a" not in css and "#f5e6e8" not in css)
check("niente effetti scintillanti (particelle, glint, bokeh, iridescenze)", all(x not in home for x in ('id="pageFx"', 'id="heroFx"', "hero-lights")) and "function goldDust" not in js and "page-fx" not in css and "hero-fx" not in css and "@keyframes pearl" not in css)
check("sfondo pagina bianco puro", "html,body{background:#fff}" in css and "body:before" not in css)
check("tipografia moderna: Montserrat + Space Grotesk + Inter, niente Playfair", '"Montserrat"' in css and '"Space Grotesk"' in css and '"Inter"' in css and "Playfair" not in css and "playfair" not in home)
check("numeri di sezione enormi (counter) e titoli pesanti", "counter(sec,decimal-leading-zero)" in css and "font-weight:800" in css)
import os
check("font locali presenti", all(os.path.exists(os.path.join("app/static/fonts", f)) for f in ("montserrat-latin-wght-normal.woff2", "space-grotesk-latin-wght-normal.woff2", "inter-latin-wght-normal.woff2")))

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
# intro: leggibilità (la misura reale è in tests/test_intro_contrasto.py)
check("intro: scrim scuro forte + controlli su fondo scuro", ".intro-vig{background:" in css and "rgba(8,15,32,.97)" in css and ".intro .chip{background:rgba(8,15,32,.82)" in css and ".intro-bars i{height:5px" in css)
check("chip dei form non sporcano più altri pulsanti (.chips .chip)", ".chips .chip span{" in css and "\n.chip span{" not in css)
# migliorie da esperto
check("fascia di fiducia sotto la hero con dati reali", 'class="trust"' in home and "24/7" in home and "Napoli e tutta Italia" in home and "Risponde direttamente Pasquale" in home)
check("banda CTA strategica con preventivo, chiamata e WhatsApp", 'class="cta-band dark"' in home and "Blocchiamola" in home and "wa.me/393661782548" in home.split('class="cta-band dark"')[1].split("</section>")[0])
check("dati strutturati FAQPage per Google", '"FAQPage"' in home and '"Question"' in home and "Dove lavorate?" in home.split('"FAQPage"')[1])
check("FAQ emergenza aggiornata al nuovo pulsante AI", "assistente AI" in home.split("Siete disponibili per le urgenze?")[1][:400])
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
