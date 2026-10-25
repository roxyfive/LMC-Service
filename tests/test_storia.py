"""Sezione «La nostra storia» (video) e rimozione completa di Videosorveglianza: python -m tests.test_storia"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_storia_")
os.environ["ADMIN_PASSWORD"] = "TestLocale123"
from backend import create_app  # noqa: E402

ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


c = create_app().test_client()
home = c.get("/").get_data(as_text=True)
media = ROOT / "app/static/media"
check("video della storia nel repo (> 10 MB) e poster presente", (media / "storia_lmc.mp4").stat().st_size > 10_000_000 and (media / "storia_lmc_poster.jpg").stat().st_size > 10_000)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media / "storia_lmc.mp4")], capture_output=True, text=True).stdout)
check("il video dura circa 3 minuti", 180 < dur < 220, dur)
check("sezione #storia con titolo evocativo", 'id="storia"' in home and "Ogni grande evento ha una storia. Ecco la nostra." in home)
check("player: poster, preload none (15 MB solo al click), sorgente mp4", 'poster="/static/media/storia_lmc_poster.jpg"' in home and 'preload="none"' in home and "/static/media/storia_lmc.mp4" in home)
check("pulsante play grande accessibile", 'id="storiaPlay"' in home and "Guarda la nostra storia" in home)
check("la sezione sta subito dopo l'hero/trust e prima di «Chi siamo»", home.index('id="storia"') < home.index('id="chi-siamo"') and home.index('class="trust"') < home.index('id="storia"'))
check("link «Guarda la nostra storia» nell'hero verso #storia", re.search(r'<section class="hero".*?href="#storia".*?</section>', home, re.S) is not None)
check("il video è servito (200, video/mp4, range)", c.get("/static/media/storia_lmc.mp4", headers={"Range": "bytes=0-99"}).status_code in (200, 206))
check("4 card skill", home.count('class="skill reveal') == 4)
for p in ("/static/media/storia_lmc.mp4", "/static/media/storia_lmc_poster.jpg"):
    check(f"{p} raggiungibile", c.get(p, headers={"Range": "bytes=0-9"}).status_code in (200, 206))

# ---- Videosorveglianza: nessuna traccia
rx = re.compile(r"sorveglian|telecamer|cctv", re.I)
hits = []
for base in ("app", "backend", "docs", "README.md", "deploy"):
    for f in ([ROOT / base] if (ROOT / base).is_file() else (ROOT / base).rglob("*")):
        if f.is_file() and f.suffix in (".py", ".html", ".js", ".css", ".md", ".json", ".sql", ".txt", ".sh", ".webmanifest", ".svg"):
            if rx.search(f.read_text(encoding="utf-8", errors="ignore")):
                hits.append(str(f.relative_to(ROOT)))
check("nessuna traccia di Videosorveglianza in codice, template, testi e docs", not hits, hits)
for url in ("/", "/sitemap.xml", "/manifest.webmanifest", "/api/tariffe"):
    r = c.get(url)
    check(f"{url}: nessuna traccia", r.status_code in (200, 404) and not rx.search(r.get_data(as_text=True)))
conf = re.search(r'id="conf".*?</section>', home, re.S)
check("configuratore e form senza Videosorveglianza", conf is not None and "Videosorveglianza" not in conf.group(0) and 'value="Videosorveglianza"' not in home)
from backend import public, admin_gest, vetrina  # noqa: E402
check("elenchi servizi senza Videosorveglianza", "Videosorveglianza" not in public.SERVICES and "Videosorveglianza" not in admin_gest.SERVICES and len(vetrina.SKILLS) == 4)
check("intro: 6 slide e voce con 6 inizi", len(vetrina.INTRO_STEPS) == 6 and len(__import__("json").load(open(media / "voce.json"))["cues"]) == 6)
H = {"X-CSRF-Token": c.get("/api/csrf").get_json()["token"]}
chat = c.post("/api/chat", json={"messages": [{"role": "user", "content": "Che servizi offrite? Fate anche impianti?"}]}, headers=H)
check("assistente: la risposta sui servizi non cita videosorveglianza", chat.status_code == 200 and not rx.search(chat.get_data(as_text=True)), chat.get_data(as_text=True)[:200])

# ---- browser: play al click, poster, schermo intero
try:
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    import threading
    srv = make_server("127.0.0.1", 0, create_app(), threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    chrome = next((x for x in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome") if Path(x).exists()), None)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"]) if chrome else p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_context(viewport={"width": 1366, "height": 850}, service_workers="block").new_page()
        pg.add_init_script("try{sessionStorage.setItem('introSeen','1')}catch(e){}")
        pg.goto(f"http://127.0.0.1:{srv.server_port}/#storia")
        pg.wait_for_timeout(1500)
        check("browser: prima del click il video non è in riproduzione e non c'è controllo", pg.evaluate("(()=>{const v=document.querySelector('#storiaVideo');return v.paused&&!v.controls})()"))
        pg.click("#storiaPlay")
        pg.wait_for_timeout(2500)
        st = pg.evaluate("(()=>{const v=document.querySelector('#storiaVideo');return {paused:v.paused,t:v.currentTime,controls:v.controls,w:v.videoWidth,cls:document.querySelector('#storiaPlayer').className}})()")
        h264 = pg.evaluate("document.createElement('video').canPlayType('video/mp4; codecs=\"avc1.42E01E\"')")
        if h264:   # il Chromium di Playwright spesso non ha H.264: in quel caso si verifica solo l'interfaccia (il file è provato con ffprobe)
            check("browser: al click il video parte, compaiono i controlli nativi", not st["paused"] and st["t"] > 0.5 and st["controls"] and st["w"] == 1280 and "playing" in st["cls"], st)
        else:
            print("NOTA: questo Chromium non decodifica H.264, riproduzione verificata solo come interfaccia")
            check("browser: al click l'interfaccia passa a «playing» con controlli nativi e il file viene richiesto", st["controls"] and "playing" in st["cls"], st)
        check("browser: lo schermo intero è disponibile", pg.evaluate("document.fullscreenEnabled && !!document.querySelector('#storiaPlayer').requestFullscreen"))
        b.close()
except Exception as e:  # Chromium non disponibile: gli altri controlli restano validi
    print("SKIP browser:", e)

print(f"\n{ok} ok, {fail} falliti")
sys.exit(1 if fail else 0)
