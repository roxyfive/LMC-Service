"""Backup + copia su IONOS Object Storage, provata DAVVERO con rclone contro un S3 emulato (moto).
python -m tests.test_backup_cloud
Richiede (solo per questo test; altrimenti SKIP):  pip install "moto[server]" rclone-bin
  (cerca moto_server e rclone nella cartella indicata da LMC_S3TEST_BIN, nel PATH o in /tmp/claude-0/s3venv/bin)
Verifica: cifratura di TUTTO (anche nel cloud), copia + verifica (dimensione e impronta), rilevamento di file troncati o
alterati, avvisi, rotazione sul cloud, elenco e ripristino dal cloud, controllo del backup mancante, nessuna chiave in git."""
import json
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
DEPLOY = ROOT / "deploy"
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


def find(tool):
    for d in (os.getenv("LMC_S3TEST_BIN"), "/tmp/claude-0/s3venv/bin"):
        if d and (Path(d) / tool).exists():
            return str(Path(d) / tool)
    return shutil.which(tool)


MOTO, RCLONE = find("moto_server"), find("rclone")
if not (MOTO and RCLONE):
    print("SKIP moto_server/rclone non disponibili (pip install \"moto[server]\" rclone-bin)")
    raise SystemExit(0)

work = Path(tempfile.mkdtemp(prefix="lmc_cloud_"))
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
moto = subprocess.Popen([MOTO, "-H", "127.0.0.1", "-p", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/moto-api/", timeout=1)
            break
        except Exception:
            time.sleep(.3)
    ENDPOINT = f"http://127.0.0.1:{port}"
    appdir, bdir = work / "app", work / "backups"
    (appdir / "data" / "uploads").mkdir(parents=True)
    (appdir / "foto" / "organizzate" / "hero").mkdir(parents=True)
    (appdir / "deploy").mkdir()
    # database vero (con una chiave API in chiaro nella tabella secrets, come fa l'admin)
    os.environ.update(DATA_DIR=str(appdir / "data"), ADMIN_PASSWORD="TestLocale123", LMC_NO_BG="1")
    sys.path.insert(0, str(ROOT))
    from backend import create_app
    from backend.db import set_secret
    app = create_app()
    with app.app_context():
        set_secret("twilio_auth_token", "TOKEN-TWILIO-SEGRETISSIMO")
    (appdir / "data" / "uploads" / "x.webp").write_bytes(os.urandom(300_000))
    (appdir / "foto" / "organizzate" / "hero" / "a.jpg").write_bytes(os.urandom(200_000))
    (appdir / ".env").write_text("TWILIO_AUTH_TOKEN=env-token-segreto\nSMTP_PASSWORD=smtp-pass-segreta\n")
    (work / "pass").write_text("password-di-test-backup\n")
    SECRET_KEY_IONOS = "chiave-segreta-ionos-0123456789"
    alerts = work / "alerts.txt"
    alert_cmd = work / "alert.sh"
    alert_cmd.write_text(f'#!/bin/bash\necho "$1 | $2" >> {alerts}\n'); alert_cmd.chmod(0o755)
    conf = work / "lmc-backup.conf"

    def write_conf(endpoint=ENDPOINT, extra=""):
        conf.write_text(f"""APP_DIR={appdir}
BACKUP_DIR={bdir}
PASS_FILE={work/'pass'}
KEEP_DAYS=7
S3_ENDPOINT={endpoint}
S3_ACCESS_KEY=AKIATESTIONOS
S3_SECRET_KEY={SECRET_KEY_IONOS}
S3_BUCKET=lmc-backup
S3_PREFIX=lmc
{extra}""")
        conf.chmod(0o600)

    env = dict(os.environ, LMC_BACKUP_CONF=str(conf), ALERT_CMD=str(alert_cmd), LMC_NO_RUNUSER="1",
               PATH=f"{Path(RCLONE).parent}:{os.environ['PATH']}")
    for k in ("DATA_DIR",):
        env.pop(k, None)
    write_conf()

    def sh(*args, **kw):
        e = dict(env, **kw.pop("env", {}))
        return subprocess.run(["bash", *map(str, args)], env=e, capture_output=True, text=True, timeout=300)

    def rc(*args):
        e = dict(env, RCLONE_CONFIG="/dev/null", RCLONE_CONFIG_T_TYPE="s3", RCLONE_CONFIG_T_PROVIDER="Other", RCLONE_CONFIG_T_ACCESS_KEY_ID="x",
                 RCLONE_CONFIG_T_SECRET_ACCESS_KEY="x", RCLONE_CONFIG_T_ENDPOINT=ENDPOINT, RCLONE_CONFIG_T_NO_CHECK_BUCKET="false")
        return subprocess.run([RCLONE, *args], env=e, capture_output=True, text=True, timeout=120)

    rc("mkdir", "t:lmc-backup")
    ls = lambda: json.loads(rc("lsjson", "t:lmc-backup/lmc", "--files-only").stdout or "[]")

    # ---------- vecchio backup sul cloud (per provare la rotazione remota) ----------
    old_dir = work / "vecchio"; old_dir.mkdir()
    oldf = old_dir / "lmc-data-2020-01-01_0330.tar.gz.enc"; oldf.write_bytes(b"vecchissimo")
    os.utime(oldf, (time.time() - 9 * 86400,) * 2)
    recent = old_dir / "lmc-data-2026-01-01_0330.tar.gz.enc"; recent.write_bytes(b"recente")
    os.utime(recent, (time.time() - 3 * 86400,) * 2)
    rc("copy", str(old_dir), "t:lmc-backup/lmc")

    # ---------- 1) backup notturno completo ----------
    r = sh(DEPLOY / "backup.sh")
    out = r.stdout + r.stderr
    check("backup.sh con copia IONOS termina con successo (exit 0)", r.returncode == 0, out[-800:])
    check("il log dichiara copia ok e verificata", "copia su IONOS ok e verificata" in out and out.count("verifica cloud ok") == 2, out[-600:])
    local = sorted(p.name for p in bdir.glob("lmc-*"))
    data_f = next(bdir.glob("lmc-data-20*_*.tar.gz.enc"), None)
    sec_f = next(bdir.glob("lmc-secrets-*.enc"), None)
    check("locale: archivio dati e segreti entrambi CIFRATI (.enc)", data_f is not None and sec_f is not None and not list(bdir.glob("lmc-data-20*_*.tar.gz")), local)
    check("locale: nessun contenuto leggibile (né token né database)", all(b"TOKEN-TWILIO" not in p.read_bytes() and b"SQLite format" not in p.read_bytes() and b"env-token" not in p.read_bytes() for p in bdir.glob("lmc-*.enc")))
    remote = {x["Name"]: x for x in ls()}
    check("cloud: i due file nuovi sono arrivati con la stessa dimensione", data_f.name in remote and sec_f.name in remote and remote[data_f.name]["Size"] == data_f.stat().st_size and remote[sec_f.name]["Size"] == sec_f.stat().st_size, list(remote))
    check("cloud: rotazione, via il backup di 9 giorni fa, resta quello di 3", "lmc-data-2020-01-01_0330.tar.gz.enc" not in remote and "lmc-data-2026-01-01_0330.tar.gz.enc" in remote, list(remote))
    check("segnalino LAST_OK scritto con cloud ok", "cloud=ok e verificata" in (bdir / "LAST_OK").read_text())
    check("le chiavi IONOS non compaiono nel log", SECRET_KEY_IONOS not in out and "AKIATESTIONOS" not in out)

    # ---------- 2) tutto ciò che sta nel cloud è cifrato ----------
    dl = work / "scaricato"; dl.mkdir()
    rc("copy", "t:lmc-backup/lmc", str(dl), "--include", "lmc-*20*_*")
    blob = b"".join(p.read_bytes() for p in dl.iterdir())
    check("cloud: nessun segreto in chiaro (token Twilio, .env, SQLite, nome dei file)", b"TOKEN-TWILIO" not in blob and b"env-token" not in blob and b"smtp-pass" not in blob and b"SQLite format" not in blob and b"hero/a.jpg" not in blob)
    dec = subprocess.run(f"openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass file:{work/'pass'} -in {dl/sec_f.name} | tar -xzO ./.env", shell=True, capture_output=True, text=True)
    check("cloud: il .env si decifra solo con la password", "env-token-segreto" in dec.stdout)
    wrong = subprocess.run(f"echo sbagliata > {work/'wrong'}; openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass file:{work/'wrong'} -in {dl/sec_f.name} | tar -tz", shell=True, capture_output=True, text=True)
    check("con una password sbagliata non si legge nulla", wrong.returncode != 0 or not wrong.stdout.strip())

    # ---------- 3) verifica: file troncato o alterato sul cloud ----------
    st = sh(DEPLOY / "backup-status.sh", "--verify-remote")
    check("backup-status --verify-remote: tutto integro", st.returncode == 0, st.stdout + st.stderr)
    subprocess.run(f"printf 'troncato' | {RCLONE} rcat t:lmc-backup/lmc/{data_f.name}", shell=True, env=dict(env, RCLONE_CONFIG="/dev/null", RCLONE_CONFIG_T_TYPE="s3", RCLONE_CONFIG_T_PROVIDER="Other", RCLONE_CONFIG_T_ACCESS_KEY_ID="x", RCLONE_CONFIG_T_SECRET_ACCESS_KEY="x", RCLONE_CONFIG_T_ENDPOINT=ENDPOINT))
    alerts.write_text("")
    st = sh(DEPLOY / "backup-status.sh", "--verify-remote", "--alert")
    check("file TRONCATO sul cloud: rilevato (dimensione) + avviso", st.returncode == 1 and "dimensione" in (st.stdout + st.stderr) and "non integro" in alerts.read_text(), st.stdout + st.stderr)
    # stessa dimensione ma contenuto diverso
    size = data_f.stat().st_size
    subprocess.run(f"head -c {size} /dev/zero | {RCLONE} rcat t:lmc-backup/lmc/{data_f.name}", shell=True, env=dict(env, RCLONE_CONFIG="/dev/null", RCLONE_CONFIG_T_TYPE="s3", RCLONE_CONFIG_T_PROVIDER="Other", RCLONE_CONFIG_T_ACCESS_KEY_ID="x", RCLONE_CONFIG_T_SECRET_ACCESS_KEY="x", RCLONE_CONFIG_T_ENDPOINT=ENDPOINT))
    st = sh(DEPLOY / "backup-status.sh", "--verify-remote")
    check("file con STESSA dimensione ma contenuto alterato: rilevato", st.returncode == 1 and ("contenuto non coincide" in (st.stdout + st.stderr) or "md5" in (st.stdout + st.stderr)), st.stdout + st.stderr)
    st = sh(DEPLOY / "backup-status.sh", "--verify-remote", env={"VERIFY_DOWNLOAD": "1"})
    check("anche con VERIFY_DOWNLOAD=1 (confronto byte per byte)", st.returncode == 1)
    # il backup successivo ripara da solo il file danneggiato sul cloud
    time.sleep(1.1)
    r = sh(DEPLOY / "backup.sh")
    check("il backup della notte dopo ricopia e ripara il cloud", r.returncode == 0 and "copia su IONOS ok e verificata" in r.stdout, r.stdout[-500:])

    # ---------- 4) ripristino dal cloud ----------
    lst = sh(DEPLOY / "restore.sh", "--cloud-list")
    check("restore.sh --cloud-list elenca i backup su IONOS", lst.returncode == 0 and "lmc-data-" in lst.stdout and "lmc-secrets-" in lst.stdout, lst.stdout + lst.stderr)
    shutil.rmtree(bdir)                                    # simulo la perdita del server: nessun backup locale
    (appdir / "data" / "lmc.db").write_bytes(b"ROTTO")
    shutil.rmtree(appdir / "foto"); (appdir / ".env").unlink()
    rr = sh(DEPLOY / "restore.sh", "--from-cloud", "latest", "--with-env", env={"LMC_YES": "1", "SERVICE": "servizio-inesistente"})
    good = False
    try:
        good = sqlite3.connect(appdir / "data" / "lmc.db").execute("select count(*) from admin_users").fetchone()[0] >= 1
    except Exception:
        pass
    check("restore dal cloud: database, foto, uploads e .env tornano com'erano", rr.returncode == 0 and good and (appdir / "foto/organizzate/hero/a.jpg").exists() and (appdir / "data/uploads/x.webp").exists() and "env-token-segreto" in (appdir / ".env").read_text(), rr.stdout + rr.stderr)
    con = sqlite3.connect(appdir / "data" / "lmc.db")
    check("restore: anche la chiave API nel database è tornata", con.execute("select value from secrets where key='twilio_auth_token'").fetchone()[0] == "TOKEN-TWILIO-SEGRETISSIMO")
    check("restore: lo stato precedente è conservato", any(p.name.startswith("data.prima-del-ripristino") for p in appdir.iterdir()))
    wrongpw = sh(DEPLOY / "restore.sh", "--from-cloud", "latest", env={"LMC_YES": "1", "SERVICE": "x", "PASS_FILE": str(work / "wrong")})
    check("restore con password sbagliata: si ferma SENZA toccare nulla", wrongpw.returncode != 0 and "non ho toccato nulla" in (wrongpw.stdout + wrongpw.stderr) and good, wrongpw.stdout + wrongpw.stderr)

    # ---------- 5) guasti: cloud irraggiungibile, chiavi sbagliate ----------
    bdir.mkdir(exist_ok=True)
    alerts.write_text("")
    write_conf(endpoint="http://127.0.0.1:9")
    r = sh(DEPLOY / "backup.sh")
    check("cloud irraggiungibile: exit 3, backup locale comunque fatto, avviso inviato", r.returncode == 3 and list(bdir.glob("lmc-data-*.enc")) and "NON riuscita" in alerts.read_text(), r.stdout + r.stderr)
    check("dopo un fallimento cloud LAST_OK non viene aggiornato", not (bdir / "LAST_OK").exists())
    write_conf(); (work / "pass").write_text("password-di-test-backup\n")
    (bdir / "LAST_OK").write_text("time=2020-01-01T00:00:00+00:00\ncloud=ok\n")
    alerts.write_text("")
    st = sh(DEPLOY / "backup-status.sh", "--check", "--alert")
    check("backup troppo vecchio (mancato): --check fallisce e avvisa", st.returncode == 1 and "MANCANTE" in alerts.read_text(), st.stdout + st.stderr)
    r = sh(DEPLOY / "backup.sh")
    st = sh(DEPLOY / "backup-status.sh", "--check", "--alert")
    check("dopo un backup riuscito --check è ok", r.returncode == 0 and st.returncode == 0, r.stdout + st.stdout)
    r = sh(DEPLOY / "backup.sh", env={"PASS_FILE": str(work / "assente")})
    check("senza password di cifratura non salva nulla in chiaro e avvisa", r.returncode == 1 and "mai dati in chiaro" in r.stdout and "password di cifratura" in alerts.read_text(), r.stdout + r.stderr)
    r = sh(DEPLOY / "backup.sh", env={"ENCRYPT": "0"})
    check("copia cloud con ENCRYPT=0 rifiutata (mai in chiaro nel cloud)", r.returncode == 1 and "mai nulla in chiaro" in r.stdout, r.stdout + r.stderr)
    conf.chmod(0o644)
    r = sh(DEPLOY / "backup.sh")
    check("conf con permessi larghi: avviso chmod 600", "chmod 600" in r.stdout, r.stdout[-400:])
    conf.chmod(0o600)

    # ---------- 6) avviso reale tramite il sito (email in outbox.log) ----------
    adata = work / "alertdata"; adata.mkdir()
    ar = subprocess.run([sys.executable, str(DEPLOY / "backup-alert.py"), "Backup NON riuscito (prova)", "messaggio di prova"], cwd=ROOT,
                        env=dict(os.environ, DATA_DIR=str(adata), OWNER_EMAIL="titolare@example.it", ADMIN_PASSWORD="TestLocale123", LMC_NO_BG="1", SMTP_HOST=""), capture_output=True, text=True)
    ob = (adata / "outbox.log").read_text() if (adata / "outbox.log").exists() else ""
    check("backup-alert.py: email al titolare tramite il sito", ar.returncode == 0 and "titolare@example.it" in ob and "Backup NON riuscito (prova)" in ob, ar.stdout + ar.stderr + ob[:200])

    # ---------- 7) chiavi IONOS e git ----------
    ign = subprocess.run(["git", "check-ignore", "-v", "deploy/lmc-backup.conf"], cwd=ROOT, capture_output=True, text=True)
    check("deploy/lmc-backup.conf (con le chiavi IONOS) è ignorato da git", ign.returncode == 0, ign.stdout)
    ex_ign = subprocess.run(["git", "check-ignore", "deploy/lmc-backup.conf.example"], cwd=ROOT, capture_output=True, text=True)
    check("il modello .example resta versionato e senza chiavi", ex_ign.returncode != 0 and not re.search(r"^S3_(ACCESS|SECRET)_KEY=\S", (DEPLOY / "lmc-backup.conf.example").read_text(), re.M))
    tracked = subprocess.run(["git", "ls-files", "deploy"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    check("nessun file con chiavi nella cartella deploy versionata", "deploy/lmc-backup.conf" not in tracked and not any(t.endswith((".key", ".pem", ".enc")) for t in tracked), tracked)
    cron = (DEPLOY / "lmc-backup.cron").read_text()
    check("cron: backup alle 03:30 e controllo alle 08:00", re.search(r"^30 3 \* \* \* root /srv/lmc/deploy/backup\.sh", cron, re.M) and re.search(r"^0 8 \* \* \* root /srv/lmc/deploy/backup-status\.sh --check --alert", cron, re.M))
finally:
    moto.terminate()
    moto.wait(timeout=10)
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
