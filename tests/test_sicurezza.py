"""Controlli di sicurezza e di coerenza del logo: python -m tests.test_sicurezza
Header, limiti di dimensione e di frequenza, cache dell'admin, segreti non tracciati, nessun riferimento al vecchio logo."""
import os
import re
import subprocess
import tempfile
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_sic_")
os.environ["ADMIN_PASSWORD"] = "TestLocale123"
os.environ["COOKIE_SECURE"] = "1"
from backend import create_app, mailer

ROOT = Path(__file__).resolve().parent.parent
app = create_app()
c = app.test_client()
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


home = c.get("/")
h = home.headers
tok = re.search(r'name="csrf" content="([0-9a-f]+)"', home.get_data(as_text=True)).group(1)
H = {"X-CSRF-Token": tok}
check("header: nosniff, frame, referrer", h["X-Content-Type-Options"] == "nosniff" and h["X-Frame-Options"] == "SAMEORIGIN" and "Referrer-Policy" in h)
check("header: CSP (plugin, base, form, frame)", all(x in h["Content-Security-Policy"] for x in ("object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'self'")))
check("header: Permissions-Policy con microfono solo al sito", "microphone=(self)" in h["Permissions-Policy"] and "camera=()" in h["Permissions-Policy"])
check("header: HSTS con COOKIE_SECURE=1", "max-age=" in h.get("Strict-Transport-Security", ""))
check("header: la home non è no-store, l'admin sì", "no-store" not in h.get("Cache-Control", "") and "no-store" in c.get("/admin/login").headers.get("Cache-Control", ""))
check("cookie di sessione: HttpOnly + SameSite + Secure", all(x in home.headers.get("Set-Cookie", "") for x in ("HttpOnly", "SameSite=Lax", "Secure")))

# dimensione delle richieste: pubbliche e login admin max 1 MB; l'admin autenticato può caricare file grandi
grande = b"x" * (1024 * 1024 + 10)
check("pubblico: corpo > 1 MB rifiutato (413)", c.post("/api/appuntamento", data=grande, headers={**H, "Content-Type": "application/json"}).status_code == 413)
check("login admin: corpo > 1 MB rifiutato senza accesso (413)", c.post("/admin/login", data=grande, headers={"Content-Type": "application/octet-stream"}).status_code == 413)
ca = app.test_client()
t2 = re.search(r'name="csrf" value="([0-9a-f]+)"', ca.get("/admin/login").get_data(as_text=True)).group(1)
check("login admin ok", ca.post("/admin/login", data={"csrf": t2, "username": "admin", "password": "TestLocale123"}).status_code == 302)
check("admin autenticato: il limite di 1 MB non si applica", ca.post("/admin/foto/riordina", data=grande, headers={"Content-Type": "application/octet-stream"}).status_code != 413)

# frequenza: appuntamenti, preventivi, chat
import backend.notify as notify
notify._hits.clear()
codes = [c.post("/api/appuntamento", json={"name": "A", "phone": "1", "email": "x"}, headers=H).status_code for _ in range(10)]
check("appuntamenti: 429 dopo 8 richieste", 429 in codes and codes.index(429) == 8, codes)
codes = [c.post("/api/preventivo", json={"name": "A", "phone": "1", "email": "x"}, headers=H).status_code for _ in range(10)]
check("preventivi: 429 dopo 8 richieste", 429 in codes and codes.index(429) == 8, codes)
codes = [c.post("/api/chat", json={"messages": [{"role": "user", "content": "ciao"}]}, headers=H).status_code for _ in range(42)]
check("chat: 200 fino a 40 messaggi, poi 429", codes[:40] == [200] * 40 and codes[40] == 429, codes[38:42])
check("senza CSRF: chat, preventivo, emergenza rifiutati", all(c.post(u, json={}).status_code == 400 for u in ("/api/chat", "/api/preventivo", "/api/emergenza", "/api/appuntamento")))
check("admin senza accesso: reindirizza al login", all(c.get(u).status_code == 302 for u in ("/admin/", "/admin/documenti", "/admin/impostazioni", "/admin/foto", "/admin/richieste")))

# email: oggetto su una riga anche con a-capo nei dati
sent = {}
import smtplib


class FakeSMTP:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self): pass
    def login(self, *a): pass
    def send_message(self, m): sent["subject"] = m["Subject"]


os.environ.update(SMTP_HOST="x", SMTP_USER="u", SMTP_PASSWORD="p", MAIL_FROM="m@example.com")
real = smtplib.SMTP
smtplib.SMTP = FakeSMTP
mailer.send_mail("a@example.com", "Ciao Mario\r\nBcc: spia@example.com", "corpo")
smtplib.SMTP = real
check("email: oggetto senza a-capo iniettati", "\n" not in sent.get("subject", "x\n") and "\r" not in sent.get("subject", ""), sent)

# segreti e file sensibili non tracciati
tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
check("git: nessun .env, chiave, database o backup tracciato", not [f for f in tracked if re.search(r"(^|/)\.env$|\.key$|\.pem$|\.db$|\.sqlite|\.enc$|secret\.key", f)])
sw = (ROOT / "app/static/js/sw.js").read_text(encoding="utf-8")
check("service worker: non mette in cache admin, api, appuntamenti, webhook", all(f"startsWith('{p}')" in sw for p in ("/admin", "/api", "/appuntamento", "/webhook")))

# logo: tutti i file citati esistono e nessun riferimento al vecchio logo
codice = ""
for f in tracked:
    if f.endswith((".py", ".html", ".js", ".css", ".json", ".sh")) and not f.startswith(("_vecchi_loghi/", "tests/test_sicurezza")):
        codice += (ROOT / f).read_text(encoding="utf-8", errors="ignore")
mancanti = [m for m in set(re.findall(r"/static/img/[A-Za-z0-9_.-]+", codice)) if not (ROOT / "app" / m.lstrip("/")).exists()]
check("logo: ogni /static/img/ citato esiste", not mancanti, mancanti)
check("logo: nessun riferimento al vecchio logo (logo-3d, logo-mono-white, logo-lmc.svg, logo/logo.png)", not re.search(r"logo-3d|logo-mono-white|logo-lmc\.svg|logo/logo\.png", codice))
man = c.get("/manifest.webmanifest").get_json()
check("manifest: icone any e maskable presenti", {i["purpose"] for i in man["icons"]} == {"any", "maskable"} and all((ROOT / "app" / i["src"].lstrip("/")).exists() for i in man["icons"]))
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
