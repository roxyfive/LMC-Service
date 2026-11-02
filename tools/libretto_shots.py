"""Screenshot per il libretto: sito (desktop + telefono) e admin (ruoli admin e collaboratore) su DATI DI PROVA, con numeri di richiamo (callout).

    python -m tools.libretto_shots CARTELLA_DI_USCITA        # rilancia sé stesso con un database temporaneo: non tocca mai quello vero
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHILD = "LMC_LIBRETTO_CHILD"
CHROME = next((c for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome") if Path(c).exists()), None)

# pagina -> (url, ruolo, [(selettore, numero)])    selettori: "p:Titolo" = pannello con quel titolo h2/h3; "css:..." = selettore CSS; "t:Testo" = elemento con quel testo
ADMIN = {
    "dashboard": ("/admin/", "admin", ["css:.side", "css:.cards", "p:Appuntamenti di oggi", "p:Richieste nuove", "p:Eventi in arrivo"]),
    "agenda": ("/admin/agenda?d={oggi}", "admin", ["css:.cal", "p:Azioni rapide"]),
    "richieste": ("/admin/richieste", "admin", ["css:table", "t:📲 Riepilogo", "t:Fai il preventivo"]),
    "preventivi": ("/admin/documenti", "admin", ["p:Nuovo preventivo", "css:table"]),
    "fatture": ("/admin/fatture", "admin", ["t:+ Nuova fattura", "css:table"]),
    "fattura": ("/admin/fatture/{fattura}", "admin", ["p:Dati", "p:Acconti e incassi", "t:Registra incasso", "t:Segna come pagata"]),
    "fattura-impostazioni": ("/admin/fatture/impostazioni", "admin", []),
    "acconti": ("/admin/acconti", "admin", ["css:.cards", "p:Registra un pagamento"]),
    "tariffe": ("/admin/tariffe", "admin", ["p:Nuova voce", "p:Listino"]),
    "statistiche": ("/admin/statistiche", "admin", ["css:.cards", "p:Incassi per mese", "p:Eventi per tipo", "p:Servizi più richiesti"]),
    "galleria": ("/admin/foto", "admin", ["css:.upform", "css:.photos"]),
    "recensioni": ("/admin/recensioni", "admin", ["p:Chiedi una recensione", "t:✔ Approva e pubblica"]),
    "utenti": ("/admin/utenti", "admin", ["p:Nuovo utente", "p:Cosa può fare ciascun ruolo"]),
    "registro": ("/admin/registro", "admin", ["css:table"]),
    "whatsapp": ("/admin/whatsapp", "admin", ["css:.cards", "p:Cosa viene inviato"]),
    "backup": ("/admin/backup", "admin", ["css:.cards", "p:Come funziona"]),
    "collab-dashboard": ("/admin/", "collab", ["css:.side", "css:.cards", "p:Appuntamenti di oggi"]),
    "collab-agenda": ("/admin/agenda?d={oggi}", "collab", ["css:.cal", "p:Azioni rapide"]),
    "collab-galleria": ("/admin/foto", "collab", ["css:.upform"]),
    "collab-negato": ("/admin/fatture", "collab", ["css:.side"]),
    "login": ("/admin/login", None, []),
}
MOBILE_ADMIN = ["dashboard", "agenda", "richieste", "fattura", "collab-dashboard"]
SITO = [("#hero", "home"), ("#storia", "storia"), ("#chi-siamo", "chi"), ("#skill", "skill"), ("#eventi", "galleria"), ("#show-demo", "video"),
        ("#configuratore", "configuratore"), ("#richieste", "form"), ("#contatti", "contatti"), ("footer", "footer")]
EXTRA = [("/privacy", "privacy"), ("/accessibilita", "accessibilita")]

MEASURE = """(sel) => {
  let el = null;
  if (sel.startsWith('css:')) el = document.querySelector(sel.slice(4));
  else if (sel.startsWith('p:')) { const t = sel.slice(2); const hs = [...document.querySelectorAll('h1,h2,h3,legend')].filter(h => h.textContent.trim().startsWith(t)); if (hs.length) el = hs[0].closest('section,.panel,form,fieldset,.card-s') || hs[0].parentElement; }
  else if (sel.startsWith('t:')) { const t = sel.slice(2); el = [...document.querySelectorAll('button,a,h2,h3,span,b')].find(e => e.textContent.trim().startsWith(t)); }
  if (!el) return null; const r = el.getBoundingClientRect();
  return r.width < 4 || r.height < 4 ? null : {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height};
}"""


def callouts(png, boxes, scale=1):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(png).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    f = ImageFont.truetype(str(ROOT / "backend/kit_assets/fonts/Inter-Bold.ttf"), 22 * scale)
    for n, b in boxes:
        x, y, w, h = [v * scale for v in (b["x"], b["y"], b["w"], b["h"])]
        if y + 20 > im.height or x > im.width:
            continue
        d.rounded_rectangle([x - 3, y - 3, min(x + w + 3, im.width - 2), min(y + h + 3, im.height - 2)], 10, outline=(255, 214, 10, 255), width=3 * scale)
        cx, cy, r = max(x - 2, 18 * scale), max(y - 2, 18 * scale), 15 * scale
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(214, 40, 40, 255), outline=(255, 255, 255, 255), width=2 * scale)
        d.text((cx, cy), str(n), font=f, fill=(255, 255, 255, 255), anchor="mm")
    im.save(png)


def main(out):
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    from werkzeug.security import generate_password_hash
    sys.path.insert(0, str(ROOT))
    from backend import create_app, kit_demo
    from backend.db import q, ex
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    app = create_app()
    with app.app_context():
        kit_demo.populate()
        from datetime import datetime
        from backend.config import DATA
        (DATA / "backup-status.txt").write_text(f"time={datetime.now().astimezone().isoformat(timespec='seconds')}\nstamp=demo\ndata=lmc_demo.tar.gz.enc\ncloud=ok e verificata\n", encoding="utf-8")
        ex("INSERT INTO admin_users(username,pw_hash,role,active,name,created) VALUES('marco',?,?,1,'Marco Bianchi',datetime('now'))", (generate_password_hash("DemoCollab2026!"), "collaboratore"))
        for who, act in [("admin", "Accesso"), ("admin", "Fattura emessa"), ("marco", "Foto caricate"), ("admin", "Acconto registrato"), ("marco", "Accesso negato")]:
            ex("INSERT INTO audit_log(username,role,action,detail,ip) VALUES(?,?,?,?,?)", (who, "admin" if who == "admin" else "collaboratore", act, "dati di prova", "127.0.0.1"))
        from datetime import date
        ids = dict(oggi=date.today().isoformat(), fattura=q("SELECT id FROM invoices WHERE status='emessa' ORDER BY id LIMIT 1", one=True)["id"])
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    report = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"]) if CHROME else p.chromium.launch(args=["--no-sandbox"])
        for dev, vp, sc in (("desktop", {"width": 1366, "height": 880}, 1), ("mobile", {"width": 390, "height": 844}, 2)):
            ctxs = {}
            for role, (u, pw) in {"admin": ("admin", "DemoTitolare2026!"), "collab": ("marco", "DemoCollab2026!")}.items():
                ctx = b.new_context(viewport=vp, service_workers="block", device_scale_factor=sc)
                pg = ctx.new_page()
                pg.goto(base + "/admin/login")
                pg.fill("input[name=username]", u)
                pg.fill("input[name=password]", pw)
                pg.click("button.btn")
                pg.wait_for_load_state("networkidle")
                ctxs[role] = pg
            anon = b.new_context(viewport=vp, service_workers="block", device_scale_factor=sc).new_page()
            for name, (url, role, sels) in ADMIN.items():
                if dev == "mobile" and name not in MOBILE_ADMIN and name != "login":
                    continue
                pg = ctxs[role] if role else anon
                pg.goto(base + url.format(**ids))
                pg.wait_for_load_state("networkidle")
                pg.wait_for_timeout(300)
                f = out / f"admin-{name}-{dev}.png"
                pg.screenshot(path=str(f))
                if dev == "desktop" and sels:
                    boxes = []
                    for n, s in enumerate(sels, 1):
                        r = pg.evaluate(MEASURE, s)
                        report[f"{name}:{s}"] = bool(r)
                        if r:
                            boxes.append((n, r))
                    callouts(f, boxes)
            # sito pubblico
            pp = b.new_context(viewport=vp, service_workers="block", device_scale_factor=sc).new_page()
            pp.add_init_script("try{sessionStorage.setItem('introSeen','1')}catch(e){}")
            pp.goto(base + "/")
            pp.wait_for_timeout(1500)
            pp.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))")
            pp.wait_for_timeout(1200)
            for sec, nm in SITO:
                el = pp.query_selector(sec)
                if el:
                    el.scroll_into_view_if_needed()
                    pp.wait_for_timeout(600)
                    pp.screenshot(path=str(out / f"sito-{nm}-{dev}.png"))
            for url, nm in EXTRA:
                pp.goto(base + url)
                pp.wait_for_timeout(500)
                pp.screenshot(path=str(out / f"sito-{nm}-{dev}.png"))
            ip = b.new_context(viewport=vp, service_workers="block", device_scale_factor=sc).new_page()
            ip.goto(base + "/?intro=1")
            ip.wait_for_timeout(3200)
            ip.screenshot(path=str(out / f"sito-intro-{dev}.png"))
            for c in list(ctxs.values()):
                c.context.close()
        b.close()
    (out / "_report.json").write_text(json.dumps(report, indent=1))
    print("fatto:", len(list(out.glob("*.png"))), "immagini")
    print("selettori non trovati:", [k for k, v in report.items() if not v])


if __name__ == "__main__":
    if os.environ.get(CHILD) == "1":
        main(sys.argv[1])
    else:
        tmp = tempfile.mkdtemp(prefix="lmc_libretto_")
        env = dict(os.environ, **{CHILD: "1", "DATA_DIR": tmp + "/data", "APP_MODE": "production", "ADMIN_PASSWORD": "DemoTitolare2026!", "SECRET_KEY": "libretto" * 6,
                                  "LMC_NO_BG": "1", "PUBLIC_URL": "https://lmcservice.duckdns.org"})
        r = subprocess.run([sys.executable, "-m", "tools.libretto_shots", sys.argv[1]], env=env, cwd=str(ROOT), capture_output=True, text=True, timeout=1200)
        print((r.stdout + r.stderr)[-2500:])
        sys.exit(r.returncode)
