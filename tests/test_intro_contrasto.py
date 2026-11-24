"""Leggibilità dell'intro nel caso PEGGIORE (foto completamente bianca) in un vero browser.
python -m tests.test_intro_contrasto  (serve playwright + Chromium; altrimenti SKIP)
Per ognuna delle 6 slide misura il contrasto WCAG tra il testo (didascalia, sottotitolo, contatore) e lo sfondo più chiaro
dietro di esso, e verifica che barre e pulsanti siano visibili (pulsante audio con sfondo scuro e testo chiaro)."""
import glob
import io
import os
import re
import tempfile
import threading
import time

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_intro_")
os.environ.setdefault("ADMIN_PASSWORD", "TestLocale123")
try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
except ImportError:
    print("SKIP playwright/Pillow non installati")
    raise SystemExit(0)
from werkzeug.serving import make_server
from backend import create_app

srv = make_server("127.0.0.1", 0, create_app())
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_port}/?intro=1"
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])


def ratio(a, b):
    a, b = max(a, b), min(a, b)
    return (a + .05) / (b + .05)


RECTS = """() => { const R = e => { if (!e) return null; const b = e.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height, color: getComputedStyle(e).color, bg: getComputedStyle(e).backgroundColor }; };
  const ws = [...document.querySelectorAll('#introCap .w')].map(e => e.getBoundingClientRect());
  const cap = ws.length ? { x: Math.min(...ws.map(c => c.x)), y: Math.min(...ws.map(c => c.y)), w: Math.max(...ws.map(c => c.right)) - Math.min(...ws.map(c => c.x)), h: Math.max(...ws.map(c => c.bottom)) - Math.min(...ws.map(c => c.y)), color: getComputedStyle(document.querySelector('#introCap .w')).color } : null;
  return { cap, sub: R(document.getElementById('introSub')), count: R(document.getElementById('introNum')), audio: R(document.getElementById('introAudio')), bar: R(document.querySelector('.intro-bars i')) }; }"""

exe = (glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome") or [None])[0]
worst = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
    for name, w, h in (("desktop", 1366, 800), ("mobile", 390, 844)):
        ctx = b.new_context(viewport={"width": w, "height": h}, service_workers="block")
        pg = ctx.new_page()
        pg.goto(URL)
        pg.wait_for_timeout(400)
        pg.add_style_tag(content=".slide{opacity:0!important}.intro-stage{background:#fff!important}")   # foto peggiore: tutta bianca
        seen, last, change, t0, audio = set(), None, 0, time.time(), None
        while len(seen) < 6 and time.time() - t0 < 80:
            num = pg.evaluate("document.getElementById('introNum').textContent")
            if num != last:
                last, change = num, time.time()
            if num not in seen and time.time() - change > 3.0:
                seen.add(num)
                rc = pg.evaluate(RECTS)
                audio = rc["audio"]
                pg.add_style_tag(content=".intro-copy>*,.intro-count,.intro-bars,.intro-ctrl{visibility:hidden!important}")
                im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
                pg.add_style_tag(content=".intro-copy>*,.intro-count,.intro-bars,.intro-ctrl{visibility:visible!important}")
                for k in ("cap", "sub", "count"):
                    r = rc[k]
                    box = (max(0, int(r["x"])), max(0, int(r["y"])), min(w, int(r["x"] + r["w"])), min(h, int(r["y"] + r["h"])))
                    bg = max(lum(c) for c in im.crop(box).get_flattened_data()) if hasattr(im, "get_flattened_data") else max(lum(c) for c in im.crop(box).getdata())
                    fg = lum([float(x) for x in re.findall(r"[\d.]+", r["color"])[:3]])
                    worst[f"{name}:{k}"] = min(worst.get(f"{name}:{k}", 99), ratio(fg, bg))
            pg.wait_for_timeout(200)
        check(f"{name}: tutte e 6 le slide verificate", len(seen) == 6, sorted(seen))
        a = re.findall(r"[\d.]+", audio["bg"])
        check(f"{name}: pulsante audio su fondo scuro (non bianco) con testo chiaro", float(a[0]) < 40 and float(a[3] if len(a) > 3 else 1) > .6, audio)
        check(f"{name}: barre di avanzamento alte almeno 4px", audio is not None and pg.evaluate("document.querySelector('.intro-bars i').getBoundingClientRect().height") >= 4)
        ctx.close()
    b.close()
for k, v in sorted(worst.items()):
    check(f"{k}: contrasto >= 4.5:1 anche su foto bianca ({v:.1f}:1)", v >= 4.5)
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
