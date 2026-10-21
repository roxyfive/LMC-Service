"""Screenshot del sito e dell'admin (desktop + mobile, ruoli admin e collaboratore) su un database TEMPORANEO con dati di prova.

Uso:  python -m backend.kit_shots CARTELLA_DI_USCITA [--rapido]
Non tocca mai il database vero: rilancia sé stesso con DATA_DIR temporaneo prima di importare l'app.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

CHILD = "LMC_KIT_SHOTS_CHILD"
CHROME_CANDIDATES = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome"]

# (nome, url, ruolo, selettore da attendere / None)
ADMIN_PAGES = [
    ("dashboard", "/admin/", "admin"), ("agenda", "/admin/agenda?d={oggi}", "admin"), ("richieste", "/admin/richieste", "admin"),
    ("preventivi", "/admin/documenti", "admin"), ("fatture", "/admin/fatture", "admin"), ("fattura", "/admin/fatture/{fattura}", "admin"),
    ("fattura-nuova", "/admin/fatture/nuova?da=appt:{appt}", "admin"), ("acconti", "/admin/acconti", "admin"), ("tariffe", "/admin/tariffe", "admin"),
    ("statistiche", "/admin/statistiche", "admin"), ("galleria", "/admin/foto?v=bozze", "admin"), ("recensioni", "/admin/recensioni", "admin"),
    ("utenti", "/admin/utenti", "admin"), ("registro", "/admin/registro", "admin"), ("whatsapp", "/admin/whatsapp", "admin"), ("backup", "/admin/backup", "admin"),
    ("collab-dashboard", "/admin/", "collab"), ("collab-agenda", "/admin/agenda?d={oggi}", "collab"), ("collab-galleria", "/admin/foto", "collab"),
    ("collab-negato", "/admin/fatture", "collab"),
]


def _find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def run_child(out, rapido=False):
    """Genera gli screenshot in un processo figlio con DATA_DIR temporaneo. Ritorna la lista dei file creati."""
    tmp = tempfile.mkdtemp(prefix="lmc_kit_")
    env = dict(os.environ, **{CHILD: "1", "DATA_DIR": tmp + "/data", "APP_MODE": "production", "ADMIN_PASSWORD": "DemoTitolare2026!", "SECRET_KEY": "kit" * 12,
                              "LMC_NO_BG": "1", "FOTO_DIR": str(Path(out) / "_foto_vuota") if rapido else os.environ.get("FOTO_DIR", ""), "PUBLIC_URL": "https://lmcservice.duckdns.org"})
    if not env["FOTO_DIR"]:
        env.pop("FOTO_DIR")
    r = subprocess.run([sys.executable, "-m", "backend.kit_shots", str(out)], env=env, capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent.parent), timeout=900)
    if r.returncode != 0:
        raise RuntimeError("screenshot non riusciti:\n" + r.stdout[-1500:] + r.stderr[-1500:])
    return sorted(Path(out).glob("*.png"))


def main(out):
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    from werkzeug.security import generate_password_hash
    from . import create_app, kit_demo
    from .db import q, ex
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    app = create_app()
    with app.app_context():
        kit_demo.populate()
        ex("INSERT INTO admin_users(username,pw_hash,role,active,name,created) VALUES('marco',?,?,1,'Marco Bianchi',datetime('now'))", (generate_password_hash("DemoCollab2026!"), "collaboratore"))
        for who, act in [("admin", "Accesso"), ("admin", "Fattura emessa"), ("marco", "Foto caricate"), ("admin", "Acconto registrato"), ("marco", "Accesso negato")]:
            ex("INSERT INTO audit_log(username,role,action,detail,ip) VALUES(?,?,?,?,?)", (who, "admin" if who == "admin" else "collaboratore", act, "dati di prova", "127.0.0.1"))
        from datetime import date
        ids = dict(oggi=date.today().isoformat(), fattura=q("SELECT id FROM invoices WHERE status='emessa' ORDER BY id LIMIT 1", one=True)["id"],
                   appt=q("SELECT id FROM appointments ORDER BY id LIMIT 1", one=True)["id"])
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    chrome = _find_chrome()
    done = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"]) if chrome else p.chromium.launch(args=["--no-sandbox"])
        for dev, vp in (("desktop", {"width": 1366, "height": 850}), ("mobile", {"width": 390, "height": 844})):
            ctxs = {}
            for role, (u, pw) in {"admin": ("admin", "DemoTitolare2026!"), "collab": ("marco", "DemoCollab2026!")}.items():
                ctx = b.new_context(viewport=vp, service_workers="block", device_scale_factor=1 if dev == "desktop" else 2)
                pg = ctx.new_page()
                pg.goto(base + "/admin/login")
                pg.fill("input[name=username]", u)
                pg.fill("input[name=password]", pw)
                pg.click("button.btn")
                pg.wait_for_load_state("networkidle")
                if "/password" in pg.url:        # collaboratore con password temporanea: nel kit la password è già quella definitiva
                    pass
                ctxs[role] = (ctx, pg)
            for name, url, role in ADMIN_PAGES:
                ctx, pg = ctxs[role]
                pg.goto(base + url.format(**ids))
                pg.wait_for_load_state("networkidle")
                pg.wait_for_timeout(250)
                f = out / f"admin-{name}-{dev}.png"
                pg.screenshot(path=str(f), full_page=(dev == "mobile" and False))
                done.append(str(f))
            # sito pubblico
            ctx, pg = ctxs["admin"]
            pub = b.new_context(viewport=vp, service_workers="block")
            pp = pub.new_page()
            pp.add_init_script("try{sessionStorage.setItem('introSeen','1')}catch(e){}")
            pp.goto(base + "/")
            pp.wait_for_timeout(1500)
            pp.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))")
            for sec, nm in (("#hero", "home"), ("#skill", "skill"), ("#eventi", "galleria"), ("#show-demo", "video"), ("#configuratore", "configuratore"), ("#richieste", "form"), ("#contatti", "contatti")):
                el = pp.query_selector(sec)
                if el:
                    el.scroll_into_view_if_needed()
                    pp.wait_for_timeout(700)
                    f = out / f"sito-{nm}-{dev}.png"
                    pp.screenshot(path=str(f))
                    done.append(str(f))
            for _r, (ctx, _pg) in ctxs.items():
                ctx.close()
            pub.close()
        b.close()
    (out / "_shots.json").write_text(json.dumps(done))
    print(len(done), "screenshot")


if __name__ == "__main__":
    if os.environ.get(CHILD) == "1":
        main(sys.argv[1])
    else:
        files = run_child(sys.argv[1], "--rapido" in sys.argv)
        print(len(files), "file in", sys.argv[1])
