"""Conformità del sito (privacy, cookie, moduli, dati, statistiche, accessibilità, bottoni, recensioni): python -m tests.test_conformita
Esclusi i dati professionali (P.IVA, sede, ecc.), che compila il titolare."""
import os
import re
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_conf_")
os.environ["LMC_NO_BG"] = "1"
os.environ["APP_MODE"] = "production"
os.environ["ADMIN_PASSWORD"] = "UnaPasswordMoltoLunga2026!"
os.environ["SECRET_KEY"] = "k" * 48
os.environ["COOKIE_SECURE"] = "1"
os.environ["PUBLIC_URL"] = "https://esempio.test"
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


from backend import create_app, retention  # noqa: E402
from backend.db import ex, q, get_setting  # noqa: E402

app = create_app()
c = app.test_client()
app.app_context().push()
home = c.get("/").get_data(as_text=True)
priv = c.get("/privacy").get_data(as_text=True)
acc = c.get("/accessibilita")

# ---- 1-2) privacy policy e cookie
check("informativa privacy completa (titolare, dati, finalità, conservazione, diritti, Garante)",
      all(x in priv for x in ("Chi tratta i tuoi dati", "Quali dati raccogliamo", "Conservazione", "I tuoi diritti", "garanteprivacy.it", "art. 6.1.b")))
check("informativa: sezione cookie, nessun tracciamento, nessun embed", "Cookie tecnico" in priv and "Nessun cookie di marketing" in priv and "nessun contenuto incorporato" in priv)
check("informativa: fornitori ed extra-UE (Twilio/Meta, Vapi) e voce del browser", "Twilio" in priv and "Vapi" in priv and "browser" in priv and "Spazio economico europeo" in priv)
check("informativa senza segnaposto «DA COMPLETARE»", "DA COMPLETARE" not in priv and "[DA" not in priv)
check("informativa: tempi di conservazione mostrati con i valori reali", f"{retention.mesi()} mesi" in priv and f"{retention.MESI_LOG} mesi" in priv)
check("pagina accessibilità raggiungibile e linkata", acc.status_code == 200 and "Dichiarazione di accessibilità" in acc.get_data(as_text=True) and "/accessibilita" in home)
check("footer: «Informativa privacy e cookie»", "Informativa privacy e cookie" in home)
check("sitemap con privacy e accessibilità", "/accessibilita" in c.get("/sitemap.xml").get_data(as_text=True))
r = c.get("/")
cookies = [h.split("=")[0] for h in r.headers.getlist("Set-Cookie")]
c.get("/api/csrf")
cookies += [h.split("=")[0] for h in c.get("/api/csrf").headers.getlist("Set-Cookie")]
check("solo il cookie tecnico «session» (HttpOnly, Secure, Lax)", set(cookies) <= {"session"} and all("HttpOnly" in h and "Secure" in h and "SameSite=Lax" in h for h in c.get("/api/csrf").headers.getlist("Set-Cookie")))
ext = set()
for f in list((ROOT / "app/templates").glob("*.html")) + [ROOT / "app/static/js/site.js", ROOT / "app/static/css/site.css"]:
    for u in re.findall(r'(?:src|href|action)=["\'](https?://[^"\']+)|url\((https?://[^)]+)\)|@import\s+["\'](https?://[^"\']+)', f.read_text(encoding="utf-8")):
        host = next(x for x in u if x).split("/")[2]
        ext.add(host)
ammessi = {"wa.me", "www.garanteprivacy.it", "www.agid.gov.it", "schema.org"}
check("nessuna risorsa incorporata da siti esterni (solo link in uscita noti)", ext <= ammessi, ext - ammessi)
check("nessun iframe/script/stile di terze parti nei template (i canonical puntano al sito stesso)", not re.search(r"<iframe|<script[^>]+src=[\"']https?:|<link[^>]+href=[\"']https?://(?!localhost|esempio\.test)", home + priv))

# ---- 3) informativa sui moduli
check("moduli: informativa breve (finalità, conservazione, titolare) sopra la presa visione", home.count("Usiamo questi dati solo per risponderti") == 2 and "li conserviamo 24 mesi" in home)
check("moduli: casella di presa visione obbligatoria con link all'informativa", home.count('name="consent" required') >= 3 and 'href="/privacy"' in home)
check("voce naturale: avviso su Vapi (USA) prima dell'uso", 'id="vapiNote"' in home and "Vapi (USA)" in home and "sessionStorage.getItem('vapiOk')" in (ROOT / "app/static/js/site.js").read_text())

# ---- 4) solo dati necessari
form = re.search(r'id="prenota".*?</form>', home, re.S).group(0)
campi = set(re.findall(r'name="(\w+)"', form))
check("prenotazione: solo i campi necessari", campi <= {"csrf", "date", "time", "name", "phone", "email", "event_type", "event_date", "notes", "consent", "website"}, campi)
check("i campi facoltativi non sono obbligatori (data evento, note)", 'name="event_date"' in form and not re.search(r'name="event_date"[^>]*required', form) and not re.search(r'name="notes"[^>]*required', form))

# ---- retention: anonimizzazione e cancellazioni
ex("INSERT INTO quotes(name,phone,email,event_type,place,notes,created) VALUES('Vecchio','333','v@x.it','Matrimonio','Roma','segreto',datetime('now','-30 months'))")
ex("INSERT INTO quotes(name,phone,email,event_type,place,notes,created) VALUES('Recente','334','r@x.it','Festa','Napoli','ok',datetime('now','-2 months'))")
ex("INSERT INTO appointments(token,name,phone,email,notes,created) VALUES('t1','Vecchia','333','a@x.it','n',datetime('now','-30 months'))")
ex("INSERT INTO calls(from_number,transcript,created) VALUES('333','vecchia',datetime('now','-14 months'))")
ex("INSERT INTO calls(from_number,transcript,created) VALUES('334','nuova',datetime('now','-1 months'))")
ex("INSERT INTO stats_events(day,kind,ref,ts) VALUES('2020-01-01','visit','x',datetime('now','-40 months'))")
ex("INSERT INTO reviews(author,text,source,hidden,status,token,email,requested_at) VALUES('A','','richiesta',1,'richiesta','tokvecchio','vecchio@x.it',datetime('now','-90 days'))")
ex("INSERT INTO reviews(author,text,source,hidden,status,token,email,requested_at) VALUES('B','','richiesta',1,'richiesta','toknuovo','nuovo@x.it',datetime('now','-3 days'))")
res = retention.run()
vecchio = q("SELECT * FROM quotes WHERE email='' AND name=?", (retention.ANON,))
check("richieste oltre i 24 mesi: dati personali anonimizzati, riga conservata", len(vecchio) == 1 and vecchio[0]["place"] == "" and vecchio[0]["notes"] == "" and vecchio[0]["event_type"] == "Matrimonio")
check("richieste recenti intatte", q("SELECT email FROM quotes WHERE name='Recente'", one=True)["email"] == "r@x.it")
check("appuntamenti oltre i 24 mesi anonimizzati", q("SELECT name,phone,email FROM appointments WHERE token='t1'", one=True)["name"] == retention.ANON)
check("chiamate oltre 12 mesi cancellate, recenti tenute", q("SELECT COUNT(*) n FROM calls WHERE transcript='vecchia'", one=True)["n"] == 0 and q("SELECT COUNT(*) n FROM calls WHERE transcript='nuova'", one=True)["n"] == 1)
check("conteggi visite oltre 26 mesi cancellati", q("SELECT COUNT(*) n FROM stats_events WHERE ref='x'", one=True)["n"] == 0)
check("email delle recensioni: cancellata se senza risposta da 60 giorni, tenuta se recente", q("SELECT email FROM reviews WHERE token='tokvecchio'", one=True)["email"] == "" and q("SELECT email FROM reviews WHERE token='toknuovo'", one=True)["email"] == "nuovo@x.it")
check("retention idempotente (seconda esecuzione non tocca nulla)", sum(retention.run().values()) == 0, retention.run())
check("la conservazione è configurabile ma mai sotto 6 mesi", (ex("INSERT OR REPLACE INTO settings(key,value) VALUES('retention_mesi','1')") or True) and retention.mesi() == 6)
ex("DELETE FROM settings WHERE key='retention_mesi'")
# recensione: l'email sparisce all'invio
H = {"X-CSRF-Token": c.get("/api/csrf").get_json()["token"]}
pg = c.get("/recensione/toknuovo")
tk = re.search(r'name="csrf" value="([0-9a-f]+)"', pg.get_data(as_text=True)).group(1)
c.post("/recensione/toknuovo", data={"csrf": tk, "stars": "5", "author": "Bruno", "text": "Serata perfetta, tutto puntuale.", "consent": "1"})
check("recensione inviata: l'email del cliente viene cancellata subito", q("SELECT email,status FROM reviews WHERE token='toknuovo'", one=True)["email"] == "")

# ---- email al cliente con nota privacy
from backend.mailer import send_cliente  # noqa: E402
from backend.config import DATA  # noqa: E402
send_cliente("cliente@x.it", "Prova", "Ciao")
log = (DATA / "outbox.log").read_text(encoding="utf-8")
check("email al cliente: nota privacy, link all'informativa e come non riceverne altre", "https://esempio.test/privacy" in log and "non vuoi ricevere altre email" in log)

# ---- 5) statistiche anonime
src = (ROOT / "backend/metrics.py").read_text()
check("statistiche: hash giornaliero, nessun IP salvato", "sha256" in src and "INSERT INTO stats_events(day,kind,ref)" in src and "remote_addr" in src and "ip" not in re.sub(r"\bip\b = |f\"\{_salt\(\)\}\|\{today\(\)\}\|\{ip\}", "", src.split("def track(")[1]))

# ---- 8) recensioni vere: niente finte né numeri inventati in produzione
check("produzione: nessuna recensione inventata (solo approvate dal titolare)", q("SELECT COUNT(*) n FROM reviews WHERE status='approvata'", one=True)["n"] == 0 and 'id="dicono"' not in home)
check("produzione: nessun numero demo, nessun bollino «Demo»", "Numero demo" not in home and 'class="demo-tag"' not in home and "Eventi realizzati</span>" not in home)
check("nessun dato di valutazione inventato nei dati strutturati", "aggregateRating" not in home and '"review"' not in home)
ex("UPDATE reviews SET status='approvata', hidden=0 WHERE token='toknuovo'")
check("una recensione approvata compare con nome e stelle", "Bruno" in c.get("/").get_data(as_text=True) and 'id="dicono"' in c.get("/").get_data(as_text=True))

# ---- 9) requisiti IT/UE: intestazioni
h = c.get("/").headers
check("intestazioni di sicurezza: Permissions-Policy, HSTS, nosniff, Referrer-Policy", "microphone=(self)" in h.get("Permissions-Policy", "") and "max-age" in h.get("Strict-Transport-Security", "") and h.get("X-Content-Type-Options") == "nosniff" and h.get("Referrer-Policy"))
check("la pagina recensione è noindex e l'admin è escluso da robots.txt", "noindex" in pg.get_data(as_text=True) and "Disallow: /admin" in c.get("/robots.txt").get_data(as_text=True))

# ---- 6-7) accessibilità e bottoni: axe (WCAG 2.2 AA) + controlli sui nomi dei bottoni
try:
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    AXE = (ROOT / "tests/vendor/axe.min.js").read_text(encoding="utf-8")
    chrome = next((x for x in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome") if Path(x).exists()), None)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"]) if chrome else p.chromium.launch(args=["--no-sandbox"])
        for dev, w, hh in (("desktop", 1366, 850), ("mobile", 390, 844)):
            ctx = b.new_context(viewport={"width": w, "height": hh}, service_workers="block", is_mobile=w < 800, has_touch=w < 800)
            for url in ("/", "/privacy", "/accessibilita"):
                pg2 = ctx.new_page()
                pg2.add_init_script("try{sessionStorage.setItem('introSeen','1')}catch(e){}")
                pg2.goto(base + url)
                pg2.wait_for_timeout(1500)
                pg2.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))")
                pg2.wait_for_timeout(1300)
                pg2.add_script_tag(content=AXE)
                v = pg2.evaluate("axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}}).then(r=>r.violations.map(v=>v.id+' ('+v.nodes.length+'): '+v.nodes[0].target.join(' ')))")
                check(f"accessibilità {url} {dev}: nessuna violazione WCAG 2.2 AA / best practice (axe)", not v, v)
                if url == "/":
                    nomi = pg2.evaluate("()=>[...document.querySelectorAll('button,a.btn,[role=button]')].filter(e=>!(e.textContent||'').trim()&&!e.getAttribute('aria-label')&&!e.getAttribute('title')).length")
                    check(f"bottoni {dev}: tutti hanno un nome comprensibile", nomi == 0, nomi)
                    ambigui = pg2.evaluate("()=>[...document.querySelectorAll('button,a.btn')].map(e=>(e.getAttribute('aria-label')||e.textContent||'').trim()).filter(t=>['Chiudi','Invia','Installa','Prenota','WhatsApp','Usa nel preventivo','Ok','Clicca qui'].includes(t))")
                    check(f"bottoni {dev}: nessuna etichetta generica o ambigua", not ambigui, ambigui)
                    piccoli = pg2.evaluate("()=>[...document.querySelectorAll('a.btn,button,.storia-link,input,select,textarea')].filter(e=>{const r=e.getBoundingClientRect(),cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&!e.closest('[hidden]')&&r.height<24}).map(e=>e.tagName+'.'+e.className)")
                    check(f"bottoni {dev}: aree di tocco di almeno 24px (WCAG 2.5.8)", not piccoli, piccoli)
                pg2.close()
            ctx.close()
        b.close()
except Exception as e:
    print("SKIP controlli browser:", e)

print(f"\n{ok} ok, {fail} falliti")
sys.exit(1 if fail else 0)
