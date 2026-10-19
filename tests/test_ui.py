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
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
