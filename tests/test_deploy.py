"""Test di preparazione al go-live: python -m tests.test_deploy
/health, cambio password admin, cifre e dati societari da admin, privacy, .gitignore/segreti, script di deploy (sintassi),
backup + rotazione + ripristino reali su cartelle temporanee, e avvio vero con gunicorn in APP_MODE=production."""
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_deploy_")
os.environ["ADMIN_PASSWORD"] = "TestLocale123"
from backend import create_app

app = create_app()
c = app.test_client()
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


def csrf(html):
    return re.search(r'name="csrf" (?:content|value)="([0-9a-f]+)"', html).group(1)


# ---------- /health ----------
r = c.get("/health")
j = r.get_json()
check("/health risponde 200 con stato ok", r.status_code == 200 and j["status"] == "ok" and j["db"] == "ok")
check("/health non espone dati sensibili e non va in cache", set(j) <= {"status", "db", "mode"} and r.headers.get("Cache-Control") == "no-store")

# ---------- admin: password, cifre, dati societari, privacy ----------
lg = c.get("/admin/login").get_data(as_text=True)
c.post("/admin/login", data={"csrf": csrf(lg), "username": "admin", "password": "TestLocale123"})
pg = c.get("/admin/password").get_data(as_text=True)
check("pagina Cambia password raggiungibile dal menu", "Cambia password" in pg and "/admin/password" in c.get("/admin/").get_data(as_text=True))
t = csrf(pg)
def cambia(old, new, new2):
    return c.post("/admin/password", data={"csrf": t, "old": old, "new": new, "new2": new2}).get_data(as_text=True)
check("password attuale errata rifiutata", "non è corretta" in cambia("sbagliata", "NuovaPassword99", "NuovaPassword99"))
check("password troppo corta rifiutata", "almeno 10" in cambia("TestLocale123", "corta", "corta"))
check("password diverse rifiutate", "non coincidono" in cambia("TestLocale123", "NuovaPassword99", "AltraPassword99"))
check("password cambiata", "Password cambiata" in cambia("TestLocale123", "NuovaPassword99", "NuovaPassword99"))
c2 = app.test_client()
lg2 = c2.get("/admin/login").get_data(as_text=True)
check("vecchia password non entra più", "Credenziali errate" in c2.post("/admin/login", data={"csrf": csrf(lg2), "username": "admin", "password": "TestLocale123"}).get_data(as_text=True))
c2.post("/admin/login", data={"csrf": csrf(c2.get("/admin/login").get_data(as_text=True)), "username": "admin", "password": "NuovaPassword99"})
check("nuova password entra", c2.get("/admin/").status_code == 200)

page = c.get("/admin/testi").get_data(as_text=True)
check("Admin › Testi: cifre, dati societari e dettagli privacy", 'name="stats_righe"' in page and 'name="dati_societari"' in page and 'name="privacy_extra"' in page)
form = {k: v for k, v in re.findall(r'name="([a-z_0-9]+)"[^>]*value="([^"]*)"', page)}
form.update({"csrf": csrf(page), "stats_righe": "Eventi realizzati | 87 | +\nAnni di attività | 2\nriga non valida", "dati_societari": "LMC Service di Pasquale Toppi · P.IVA 01234567890 · Napoli",
             "privacy_extra": "Fornitori: Twilio (WhatsApp), Vapi (voce). Conservazione: 24 mesi.", "email": "info@example.it"})
c.post("/admin/testi", data=form)
home = c.get("/").get_data(as_text=True)
check("cifre reali da admin (e righe non valide ignorate)", 'data-to="87"' in home and 'data-to="2"' in home and "riga non valida" not in home)
check("dati societari nel footer", "P.IVA 01234567890" in home)
priv = c.get("/privacy").get_data(as_text=True)
check("privacy: dettagli inseriti da admin e nessun [DA COMPLETARE]", "Conservazione: 24 mesi" in priv and "DA COMPLETARE" not in priv)
check("email inserita da admin compare nei contatti", "info@example.it" in home)

# ---------- documentazione di go-live ----------
guida = (ROOT / "docs" / "GUIDA-ADMIN.md").read_text()
nav = open(ROOT / "app/templates/admin/base.html").read()
labels = [re.sub(r"^[^A-Za-zÀ-ù]+", "", t).strip() for t in re.findall(r'<a href="/[^"]*"[^>]*>([^<]+)</a>', nav)]
missing = [l for l in labels if l and l.lower() not in guida.lower()]
check("la guida admin copre tutte le voci del menu", labels and not missing, missing)
check("checklist go-live con percorso e priorità per ogni voce", all(x in (ROOT / "docs" / "CHECKLIST-GO-LIVE.md").read_text() for x in ("Bloccante", "Dati societari", "ADMIN_PASSWORD", "SMTP", "APP_MODE=production", "Foto e video reali")))
dep = (ROOT / "docs" / "DEPLOY.md").read_text()
check("DEPLOY.md: IONOS, HTTPS, backup 7 giorni, ripristino, rclone, /health", all(x in dep for x in ("IONOS", "certbot", "7 giorni", "restore.sh", "rclone", "/health", "setup-vps.sh", "lmc-backup.conf", "--from-cloud", "backup-status.sh", "/etc/cron.d/lmc-backup", "03:30", "Key management", "verifica cloud ok")))

# ---------- segreti e git ----------
gi = (ROOT / ".gitignore").read_text()
for pat in (".env", "data/", "*.key", "*.db", "*.enc", "lmc-data-"):
    check(f".gitignore copre {pat}", pat in gi)
tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
bad = [f for f in tracked if re.search(r"(^|/)\.env$|secret\.key|\.db$|\.db-wal|\.pem$|\.enc$|outbox\.log", f)]
check("nessun file segreto tracciato da git", not bad, bad)
leak = subprocess.run(["git", "grep", "-nIE", r"(sk|pk)_(live|test)_[A-Za-z0-9]{12,}|AC[0-9a-f]{32}|[0-9a-f]{64}", "--", ".", ":!*.png", ":!*.webp", ":!*.woff2", ":!*.mp3", ":!*.mp4", ":!*.pdf"],
                      cwd=ROOT, capture_output=True, text=True).stdout.strip()
check("nessuna chiave/token nel codice versionato", leak == "", leak[:200])
check(".env.example e env.production.example senza valori segreti", all(not re.search(r"^(SECRET_KEY|ADMIN_PASSWORD|TWILIO_AUTH_TOKEN|VAPI_API_KEY|AI_API_KEY)=\S", (ROOT / f).read_text(), re.M) for f in (".env.example", "deploy/env.production.example")))

# ---------- script di deploy ----------
for sh in ("setup-vps.sh", "backup.sh", "restore.sh", "backup-status.sh", "lib-backup.sh"):
    check(f"deploy/{sh}: sintassi bash valida", subprocess.run(["bash", "-n", str(ROOT / "deploy" / sh)]).returncode == 0)
svc = (ROOT / "deploy" / "lmc.service").read_text()
check("lmc.service: gunicorn run:app su 127.0.0.1, EnvironmentFile, Restart", "gunicorn run:app" in svc and "127.0.0.1:8010" in svc and "EnvironmentFile=/srv/lmc/.env" in svc and "Restart=always" in svc)
ng = (ROOT / "deploy" / "nginx-lmc.conf").read_text()
check("nginx: gzip, cache statici, upload 200M, /health, rate limit webhook", all(x in ng for x in ("gzip on", "expires 7d", "client_max_body_size 200M", "location = /health", "zone=lmc_hooks")))
check("manifest PWA con sfondo bianco", c.get("/manifest.webmanifest").get_json()["background_color"] == "#ffffff")

# ---------- backup, rotazione e ripristino reali (locale: la copia cloud è provata in test_backup_cloud) ----------
work = Path(tempfile.mkdtemp(prefix="lmc_bk_"))
appdir, bdir = work / "app", work / "backups"
(appdir / "data" / "uploads").mkdir(parents=True)
(appdir / "foto" / "organizzate" / "hero").mkdir(parents=True)
shutil.copy(Path(os.environ["DATA_DIR"]) / "lmc.db", appdir / "data" / "lmc.db")
(appdir / "data" / "uploads" / "x.webp").write_bytes(b"img")
(appdir / "foto" / "organizzate" / "hero" / "a.jpg").write_bytes(b"jpg")
(appdir / "data" / "secret.key").write_text("chiave-di-sessione-segreta")
(appdir / ".env").write_text("TWILIO_AUTH_TOKEN=token-molto-segreto\n")
(work / "pass").write_text("password-di-test-backup\n")
env = dict(os.environ, APP_DIR=str(appdir), BACKUP_DIR=str(bdir), PASS_FILE=str(work / "pass"), KEEP_DAYS="7", LMC_BACKUP_CONF=str(work / "nessun.conf"),
           LMC_NO_RUNUSER="1", ALERT_CMD="true")
for k in ("S3_BUCKET", "S3_ENDPOINT", "RCLONE_REMOTE"):
    env.pop(k, None)
bdir.mkdir()
old = bdir / "lmc-data-2020-01-01_0330.tar.gz.enc"
old.write_bytes(b"vecchio")
os.utime(old, (time.time() - 9 * 86400,) * 2)
fresh = bdir / "lmc-data-fresco.tar.gz.enc"
fresh.write_bytes(b"recente")
os.utime(fresh, (time.time() - 3 * 86400,) * 2)
r = subprocess.run(["bash", str(ROOT / "deploy" / "backup.sh")], env=env, capture_output=True, text=True)
check("backup.sh (solo locale) termina con successo", r.returncode == 0, r.stdout + r.stderr)
datas = [p for p in bdir.glob("lmc-data-*.tar.gz.enc") if "fresco" not in p.name and "2020" not in p.name]
secs = list(bdir.glob("lmc-secrets-*.enc"))
check("creati archivio dati e archivio segreti, entrambi cifrati", len(datas) == 1 and len(secs) == 1 and not list(bdir.glob("lmc-data-20*_*.tar.gz")))
dec = lambda f: subprocess.run(f"openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass file:{work/'pass'} -in {f}", shell=True, capture_output=True).stdout
names = subprocess.run(["tar", "-tz"], input=dec(datas[0]), capture_output=True).stdout.decode()
check("l'archivio contiene database, uploads e foto", "./lmc.db" in names and "uploads/x.webp" in names and "foto/organizzate/hero/a.jpg" in names)
tmpdb = work / "estratto"
tmpdb.mkdir()
subprocess.run(["tar", "-xz", "-C", str(tmpdb), "./lmc.db"], input=dec(datas[0]), check=True)
con = sqlite3.connect(tmpdb / "lmc.db")
check("il database nel backup è integro e contiene i dati", con.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and con.execute("select count(*) from admin_users").fetchone()[0] >= 1)
con.close()
check("nei file di backup non c'è nulla in chiaro (.env, database)", all(b"token-molto-segreto" not in p.read_bytes() and b"SQLite format" not in p.read_bytes() for p in bdir.glob("lmc-*.enc")))
check("il .env si decifra con la password", b"token-molto-segreto" in subprocess.run(["tar", "-xzO", "./.env"], input=dec(secs[0]), capture_output=True).stdout)
check("rotazione: via i backup oltre 7 giorni, restano i recenti", not old.exists() and fresh.exists())
check("cartella backup con permessi riservati (700)", oct(bdir.stat().st_mode & 0o777) == "0o700")
r2 = subprocess.run(["bash", str(ROOT / "deploy" / "backup.sh")], env=dict(env, PASS_FILE=str(work / "assente")), capture_output=True, text=True)
check("senza password di cifratura non salva nulla (mai in chiaro) ed esce con errore", r2.returncode == 1 and "mai dati in chiaro" in r2.stdout)
# ripristino da file locale
(appdir / "data" / "lmc.db").write_bytes(b"ROTTO")
shutil.rmtree(appdir / "foto")
r3 = subprocess.run(["bash", str(ROOT / "deploy" / "restore.sh"), str(datas[0]), str(secs[0])], env=dict(env, LMC_YES="1", SERVICE="servizio-inesistente"), capture_output=True, text=True)
okdb = False
try:
    okdb = sqlite3.connect(appdir / "data" / "lmc.db").execute("select count(*) from admin_users").fetchone()[0] >= 1
except Exception:
    pass
check("restore.sh ripristina database, foto e .env", r3.returncode == 0 and okdb and (appdir / "foto/organizzate/hero/a.jpg").exists() and "token-molto-segreto" in (appdir / ".env").read_text(), r3.stdout + r3.stderr)
check("restore.sh conserva lo stato precedente", any(p.name.startswith("data.prima-del-ripristino") for p in appdir.iterdir()))

# ---------- avvio reale con gunicorn in produzione ----------
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
gdata = tempfile.mkdtemp(prefix="lmc_gun_")
genv = dict(os.environ, APP_MODE="production", DATA_DIR=gdata, TRUST_PROXY="1", COOKIE_SECURE="1", LMC_NO_BG="1", ADMIN_PASSWORD="PrimoAvvio12345", FOTO_DIR=str(work / "fotovuote"))
gun = Path(sys.executable).parent / "gunicorn"
if not gun.exists():
    print("SKIP gunicorn non installato")
else:
    log = open(Path(gdata) / "gunicorn.log", "w")
    p = subprocess.Popen([str(gun), "run:app", "--bind", f"127.0.0.1:{port}", "--workers", "2", "--threads", "2"], cwd=ROOT, env=genv, stdout=log, stderr=subprocess.STDOUT)
    body = hh = None
    try:
        for _ in range(40):
            try:
                hh = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).read().decode()
                break
            except Exception:
                time.sleep(.5)
        body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode()
    finally:
        p.terminate()
        p.wait(timeout=10)
        log.close()
    lg_txt = (Path(gdata) / "gunicorn.log").read_text()
    check("gunicorn parte e /health dice mode=production", hh is not None and '"mode":"production"' in hh.replace(" ", ""), hh)
    check("produzione: nessun bollino DEMO nella home", body is not None and "demo-tag" not in body and "foto e testi demo" not in body.lower())
    check("avvio in produzione: avviso se ADMIN_PASSWORD resta nel .env", "ADMIN_PASSWORD è ancora nel .env" in lg_txt)
    check("nessun dato sensibile nel log di avvio", "PrimoAvvio12345" not in lg_txt)

print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
