"""Tema nero/rosso: i contorni ROSSI devono comparire ovunque: python -m tests.test_tema
Un `}` in più nel CSS (già successo) fa scartare la regola seguente (le variabili del tema) e i bordi diventano bianchi:
qui si controlla il bilanciamento delle graffe e il colore REALE (calcolato dal browser) dei bordi chiave a 1366 e 390 px."""
import os
import re
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_tema_")
os.environ["LMC_NO_BG"] = "1"
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


for css in ("site.css", "admin.css"):
    t = re.sub(r"/\*.*?\*/", "", (ROOT / "app/static/css" / css).read_text(encoding="utf-8"), flags=re.S)
    d, neg = 0, False
    for ch in t:
        d += (ch == "{") - (ch == "}")
        neg = neg or d < 0
    check(f"{css}: graffe bilanciate e mai chiuse in più", d == 0 and not neg, d)

from backend import create_app  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

srv = make_server("127.0.0.1", 0, create_app(), threaded=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}"
RED = "rgb(225, 29, 20)"
chrome = next((c for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome") if Path(c).exists()), None)
JS = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const cs = getComputedStyle(e);
  return {top: cs.borderTopColor + ' ' + cs.borderTopWidth, all: [cs.borderTopColor, cs.borderRightColor, cs.borderBottomColor, cs.borderLeftColor], w: cs.borderTopWidth, shadow: cs.boxShadow}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"]) if chrome else p.chromium.launch(args=["--no-sandbox"])
    for w, h in ((1366, 850), (390, 844)):
        pg = b.new_context(viewport={"width": w, "height": h}, service_workers="block").new_page()
        pg.add_init_script("try{sessionStorage.setItem('introSeen','1')}catch(e){}")
        pg.goto(base + "/")
        pg.wait_for_timeout(1200)
        pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))")
        pg.wait_for_timeout(1200)
        check(f"{w}px: variabile --red definita dal tema", pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--red').trim()") == "#e11d14")
        check(f"{w}px: sfondo scuro del tema (non bianco)", pg.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(22, 22, 28)")
        for name, sel in (("card skill", ".skill"), ("player La nostra storia", "#storiaPlayer"), ("pulsante secondario", ".hero .btn-line"),
                          ("pulsante play storia", ".storia-ico"), ("campo del form", "#richieste input:not([type=hidden]):not([type=checkbox])"),
                          ("riquadro «in breve»", ".facts"), ("striscia fiducia", ".trust"), ("carta contatti", ".contact-card")):
            r = pg.evaluate(JS, sel)
            if r is None:
                print(f"NOTA {w}px: «{name}» ({sel}) non presente")
                continue
            check(f"{w}px: {name}: bordo rosso", RED in r["all"], r["all"])
        # pulsante secondario: all'hover si riempie di rosso
        pg.hover(".hero .btn-line")
        pg.wait_for_timeout(500)
        check(f"{w}px: pulsante secondario: riempimento rosso all'hover", pg.evaluate("getComputedStyle(document.querySelector('.hero .btn-line')).backgroundColor") == RED)
        # footer
        f = pg.evaluate("(()=>{const e=document.querySelector('footer,.foot');const cs=getComputedStyle(e);return [cs.borderTopColor,cs.boxShadow,cs.borderTopWidth]})()")
        check(f"{w}px: footer con filo rosso", RED in f[0] or "225, 29, 20" in f[1], f)
        pg2 = b.new_context(viewport={"width": w, "height": h}, service_workers="block").new_page()
        pg2.goto(base + "/?intro=1")
        pg2.wait_for_timeout(2500)
        r = pg2.evaluate(JS, ".intro-frame")
        check(f"{w}px: cornice rossa dell'intro", r is not None and "rgba(225, 29, 20" in r["top"], r)
    b.close()
print(f"\n{ok} ok, {fail} falliti")
sys.exit(1 if fail else 0)
