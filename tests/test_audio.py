"""Test audio dell'intro in un vero browser (opzionale: serve `pip install playwright` e Chromium).
python -m tests.test_audio
Verifica: clic -> musica e voce partono davvero (currentTime avanza, segnale non silenzioso), musica abbassata sotto la voce,
slide sincronizzate con le frasi, e il pulsante NON dice "attivo" se il file audio non si carica."""
import glob
import os
import tempfile
import threading

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_audio_")
os.environ.setdefault("ADMIN_PASSWORD", "TestLocale123")
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP playwright non installato (pip install playwright)")
    raise SystemExit(0)
from werkzeug.serving import make_server
from backend import create_app

srv = make_server("127.0.0.1", 0, create_app())
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_port}/"
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


PROBE = """() => { const ctx = new AudioContext(); window.__an = {};
  for (const id of ['introMusic', 'introVoce']) { const el = document.getElementById(id); if (!el) continue;
    const src = ctx.createMediaElementSource(el), an = ctx.createAnalyser(); an.fftSize = 2048; src.connect(an); an.connect(ctx.destination); window.__an[id] = an; }
  return ctx.resume().then(() => true); }"""
RMS = """() => Object.fromEntries(Object.entries(window.__an).map(([k, an]) => { const b = new Float32Array(an.fftSize); an.getFloatTimeDomainData(b);
  return [k, Math.sqrt(b.reduce((s, x) => s + x * x, 0) / b.length)]; }))"""
STATE = """() => { const m = document.getElementById('introMusic'), v = document.getElementById('introVoce');
  return { m: { paused: m.paused, t: m.currentTime, vol: m.volume, err: m.error && m.error.code },
           v: v && { paused: v.paused, t: v.currentTime }, step: document.getElementById('introNum').textContent,
           label: document.getElementById('introAudioTxt').textContent } }"""

exe = (glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome") or [None])[0]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
    ctx = b.new_context(service_workers="block")
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1200)
    has_voice = pg.evaluate("!!document.getElementById('introVoce')")
    pg.click("#introAudio"); pg.wait_for_timeout(300); pg.evaluate(PROBE); pg.wait_for_timeout(2500)
    s1, r1 = pg.evaluate(STATE), pg.evaluate(RMS)
    pg.wait_for_timeout(5500); s2 = pg.evaluate(STATE)
    check("musica in riproduzione", not s1["m"]["paused"] and s1["m"]["err"] is None and s2["m"]["t"] > s1["m"]["t"] + 3, s1)
    check("segnale musica non silenzioso", r1["introMusic"] > 0.003, r1)
    check("pulsante indica audio attivo", "attivo" in s1["label"].lower(), s1["label"])
    if has_voice:
        check("voce in riproduzione", not s1["v"]["paused"] and s2["v"]["t"] > s1["v"]["t"] + 3, s1)
        check("segnale voce non silenzioso", r1["introVoce"] > 0.003, r1)
        check("musica abbassata sotto la voce", s1["m"]["vol"] <= 0.25, s1["m"])
        check("slide 2 al cue della frase 2 (~6 s)", s2["step"] == "02", s2["step"])
    pg.click("#introAudio"); pg.wait_for_timeout(400)
    check("spegnimento", pg.evaluate("document.getElementById('introMusic').paused"))
    # file musica non caricabile -> niente falso "attivo"
    pg2 = ctx.new_page()
    pg2.route("**/music.mp3", lambda r: r.abort())
    pg2.goto(URL + "?intro=1"); pg2.wait_for_timeout(1000); pg2.click("#introAudio"); pg2.wait_for_timeout(1500)
    check("errore audio segnalato", "non riproducibile" in pg2.inner_text("#introAudioTxt").lower(), pg2.inner_text("#introAudioTxt"))
    check("nessun errore JS", not errs, errs)
    b.close()
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
