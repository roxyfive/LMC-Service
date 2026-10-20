"""Intro: nessuna sovrapposizione tra logo, contatore «07 / 07», didascalia, sottotitolo, barre e pulsanti, e nulla fuori schermo,
su 7 dimensioni di schermo (desktop, portatile basso, telefono, telefono piccolo, telefono in orizzontale).
python -m tests.test_intro_layout   (serve playwright + Chromium; altrimenti SKIP)"""
import glob
import json
import os
import tempfile
import threading

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_layout_")
os.environ.setdefault("ADMIN_PASSWORD", "TestLocale123")
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP playwright non installato")
    raise SystemExit(0)
from werkzeug.serving import make_server
from backend import create_app

srv = make_server("127.0.0.1", 0, create_app())
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_port}/?intro=1"
ok = fail = 0

JS = """(steps)=>{
 const R=(el)=>{const b=el.getBoundingClientRect();return {x:b.left,y:b.top,r:b.right,b:b.bottom}};
 const T=(el)=>{const rg=document.createRange();rg.selectNodeContents(el);const b=rg.getBoundingClientRect();return {x:b.left,y:b.top,r:b.right,b:b.bottom}};
 const cap=document.getElementById('introCap'), sub=document.getElementById('introSub'), out=[];
 for(const st of steps){
   cap.textContent=st.cap; sub.textContent=st.sub||''; sub.classList.add('in');
   const els={logo:R(document.querySelector('.intro-logo')),count:R(document.querySelector('.intro-count')),cap:T(cap),sub:T(sub),bars:R(document.getElementById('introBars')),audio:R(document.getElementById('introAudio')),skip:R(document.getElementById('introSkip'))};
   const n=Object.keys(els),bad=[];
   for(let i=0;i<n.length;i++)for(let j=i+1;j<n.length;j++){const a=els[n[i]],b=els[n[j]];if(a.x<b.r-1&&b.x<a.r-1&&a.y<b.b-1&&b.y<a.b-1)bad.push(n[i]+'×'+n[j]);}
   const off=n.filter(k=>els[k].x<-1||els[k].r>innerWidth+1||els[k].y<-1||els[k].b>innerHeight+1);
   out.push({cap:st.cap.slice(0,22),bad,off});
 }
 return out;}"""
exe = (glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome") or [None])[0]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
    for name, w, h in (("desktop 1366x800", 1366, 800), ("portatile 1366x600", 1366, 600), ("basso 1280x560", 1280, 560), ("telefono 390x844", 390, 844),
                       ("telefono 360x640", 360, 640), ("orizzontale 844x390", 844, 390), ("piccolo 320x568", 320, 568)):
        ctx = b.new_context(viewport={"width": w, "height": h}, service_workers="block")
        pg = ctx.new_page()
        pg.goto(URL)
        pg.wait_for_timeout(600)
        steps = json.loads(pg.evaluate("document.getElementById('introData').textContent"))["steps"]
        pg.add_style_tag(content=".intro-cap .w{opacity:1!important;transform:none!important;filter:none!important;animation:none!important}")
        res = pg.evaluate(JS, steps)
        probs = [(r["cap"], r["bad"], r["off"]) for r in res if r["bad"] or r["off"]]
        in_intro = pg.evaluate("document.querySelector('.intro-count').parentElement.classList.contains('intro')")
        pos = pg.evaluate("(()=>{const c=document.querySelector('.intro-count').getBoundingClientRect(),b=document.getElementById('introBars').getBoundingClientRect();return Math.abs((c.top+c.bottom)/2-(b.top+b.bottom)/2)})()")
        label = f"{name}: nessuna sovrapposizione né elementi fuori schermo ({len(res)} slide)"
        c1 = not probs
        print(("PASS " if c1 else "FAIL ") + label, "" if c1 else probs[:2])
        c2 = in_intro and pos < 14
        print(("PASS " if c2 else "FAIL ") + f"{name}: contatore allineato alla riga delle barre ({pos:.0f}px)")
        ok += c1 + c2
        fail += (not c1) + (not c2)
        ctx.close()
    b.close()
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
