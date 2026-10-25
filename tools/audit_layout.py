"""Controllo allineamenti della home e dell'intro a più dimensioni di schermo (screenshot + misure).

    python -m tools.audit_layout [CARTELLA_SCREENSHOT]      # stampa le anomalie, esce con 1 se ce ne sono
Per ogni schermo: sbordamento orizzontale della pagina, elementi che escono dallo schermo, contenuti dei blocchi centrati
con margini sinistro/destro diversi, e la sezione «La nostra storia» (titolo, riga, player) rispetto al centro."""
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

SIZES = [("mobile-piccolo", 360, 740), ("mobile", 390, 844), ("phablet", 430, 932), ("tablet", 768, 1024), ("laptop", 1366, 768), ("desktop", 1920, 1080)]
CHROME = next((c for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome") if Path(c).exists()), None)

MEASURE = """() => {
  const vw = document.documentElement.clientWidth, out = {vw, sw: document.documentElement.scrollWidth, bad: [], asym: []};
  const vis = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e); return r.width > 2 && r.height > 2 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0; };
  const label = e => (e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/).slice(0, 2).join('.') : '')).slice(0, 60);
  // 1) elementi che escono dallo schermo (a destra o a sinistra), esclusi quelli volutamente scorrevoli/nascosti
  document.querySelectorAll('body *').forEach(e => {
    if (!vis(e) || e.closest('#intro,.chat,.chat-panel,[hidden],.sr-only,.skip-link,.nav-menu:not(.open),.hero-slides,.beams,svg *,video,.marquee')) return;
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    if (cs.position === 'fixed') return;
    if (r.right > vw + 1.5 || r.left < -1.5) { let p = e.parentElement, clipped = false; while (p && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o !== 'visible') { clipped = true; break; } p = p.parentElement; } if (!clipped) out.bad.push([label(e), Math.round(r.left), Math.round(r.right)]); }
  });
  // 2) blocchi che dovrebbero essere centrati: margine sinistro = destro (tolleranza 2px)
  const sel = ['#storia .storia-head', '#storia .storia-player', '#storia .storia-head h2', '#storia .storia-head p', '#storia .kicker', '.skill-grid', '.trust-in', '#cifre .stat-grid', '#contatti .contact-grid', 'footer .foot-in', '.cta-band-in'];
  sel.forEach(s => document.querySelectorAll(s).forEach(e => { if (!vis(e)) return; const r = e.getBoundingClientRect(); const l = r.left, rr = vw - r.right; if (Math.abs(l - rr) > 2.5) out.asym.push([s, Math.round(l), Math.round(rr)]); }));
  // 3) testo della storia: il centro delle righe deve coincidere con il centro dello schermo
  out.storia = [];
  document.querySelectorAll('#storia .kicker, #storia h2, #storia .storia-head p, #storia hr.rule').forEach(e => { const rg = document.createRange(); rg.selectNodeContents(e); const rs = [...rg.getClientRects()].filter(x => x.width > 1); if (!rs.length) return; rs.forEach(x => { const c = (x.left + x.right) / 2; if (Math.abs(c - vw / 2) > 3) out.storia.push([label(e), Math.round(c - vw / 2)]); }); });
  const pl = document.querySelector('#storiaPlayer'); if (pl) { const r = pl.getBoundingClientRect(); out.player = [Math.round(r.left), Math.round(vw - r.right), Math.round(r.width)]; }
  return out;
}"""

INTRO = """() => {
  const vw = document.documentElement.clientWidth, o = [];
  const c = (s) => { const e = document.querySelector(s); if (!e) return; const r = e.getBoundingClientRect(); if (r.width < 2) return; o.push([s, Math.round(r.left), Math.round(vw - r.right), Math.round(r.width)]); };
  ['.intro-logo', '#introCap', '#introSub', '.intro-bars', '.intro-count', '.intro-ctrl', '#introAudio', '#introSkip'].forEach(c);
  const txt = (s) => { const e = document.querySelector(s); if (!e || !e.textContent.trim()) return; const rg = document.createRange(); rg.selectNodeContents(e); const rs = [...rg.getClientRects()].filter(x => x.width > 1); if (!rs.length) return; const l = Math.min(...rs.map(x => x.left)), r = Math.max(...rs.map(x => x.right)); o.push(['testo ' + s, Math.round(l), Math.round(vw - r), Math.round(r - l)]); };
  ['#introCap', '#introSub', '.intro-count'].forEach(txt);
  return {vw, sw: document.documentElement.scrollWidth, items: o};
}"""


def main(outdir=None):
    os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="lmc_audit_"))
    os.environ["LMC_NO_BG"] = "1"
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    from backend import create_app
    srv = make_server("127.0.0.1", 0, create_app(), threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    out = Path(outdir) if outdir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    problems = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"]) if CHROME else p.chromium.launch(args=["--no-sandbox"])
        for name, w, h in SIZES:
            mob = w < 800
            ctx = b.new_context(viewport={"width": w, "height": h}, service_workers="block", device_scale_factor=2 if mob else 1, has_touch=mob, is_mobile=mob)
            pg = ctx.new_page()
            pg.add_init_script("try{sessionStorage.setItem('introSeen','1')}catch(e){}")
            pg.goto(base + "/")
            pg.wait_for_timeout(1800)
            pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))")
            pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>{i.loading='eager'})")
            pg.wait_for_timeout(1600)       # lascia finire le transizioni di comparsa (.reveal)
            r = pg.evaluate(MEASURE)
            tag = f"{name} {w}px"
            if r["sw"] > r["vw"] + 1:
                problems.append(f"{tag}: la pagina scorre in orizzontale (scrollWidth {r['sw']} > {r['vw']})")
            for x in r["bad"][:12]:
                problems.append(f"{tag}: elemento fuori schermo {x[0]} (sinistra {x[1]}, destra {x[2]})")
            for x in r["asym"]:
                problems.append(f"{tag}: margini asimmetrici in {x[0]}: sinistro {x[1]}px, destro {x[2]}px")
            for x in r["storia"]:
                problems.append(f"{tag}: storia, {x[0]} decentrato di {x[1]}px")
            if r.get("player") and (min(r["player"][:2]) < 12 and w < 800):
                problems.append(f"{tag}: player troppo a contatto col bordo ({r['player'][0]}px / {r['player'][1]}px)")
            if out:
                pg.screenshot(path=str(out / f"home-{name}-{w}.png"), full_page=True)
                for sec in ("storia", "skill"):
                    el = pg.query_selector("#" + sec)
                    if el:
                        el.screenshot(path=str(out / f"{sec}-{name}-{w}.png"))
            # intro
            pg2 = ctx.new_page()
            pg2.goto(base + "/?intro=1")
            pg2.wait_for_timeout(3500)
            ri = pg2.evaluate(INTRO)
            if ri["sw"] > ri["vw"] + 1:
                problems.append(f"{tag}: intro scorre in orizzontale")
            it = {x[0]: x for x in ri["items"]}
            if w <= 600 and ".intro-bars" in it and ".intro-count" in it:
                lb, rc_ = it[".intro-bars"][1], it[".intro-count"][2]
                if abs(lb - rc_) > 4:
                    problems.append(f"{tag}: intro barre+contatore: margine sinistro {lb}px, destro {rc_}px")
            for sel, l, rr, wd in ri["items"]:
                if w <= 600 and sel in (".intro-bars", ".intro-count", "testo .intro-count"):
                    continue
                # su telefono in verticale l'intro è centrata: margini sinistro/destro uguali; su schermi larghi il layout è editoriale (a sinistra) per scelta
                if w <= 600 and abs(l - rr) > 4:
                    problems.append(f"{tag}: intro {sel} margini {l}px / {rr}px (larghezza {wd})")
                if (l < 8 or rr < 8) and wd < w - 20 or (wd >= w - 20 and (l < 8 or rr < 8) and sel != ".intro-count"):
                    problems.append(f"{tag}: intro {sel} troppo vicino al bordo ({l}px / {rr}px)")
            if out:
                pg2.screenshot(path=str(out / f"intro-{name}-{w}.png"))
            ctx.close()
        b.close()
    for x in problems:
        print("PROBLEMA", x)
    print(len(problems), "problemi" if problems else "nessun problema", f"su {len(SIZES)} schermi")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
