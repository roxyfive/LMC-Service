"""Foto doppie: avvio simultaneo di più worker (causa dei doppioni in produzione), pulizia dei doppioni già nel database,
nessun doppione nei file di foto/organizzate. python -m tests.test_foto_doppie"""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image

tmp = Path(tempfile.mkdtemp(prefix="lmc_doppie_"))
ok = fail = 0


def check(name, cond):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name)
    ok, fail = ok + bool(cond), fail + (not cond)


def jpg(seed):
    import random
    r = random.Random(seed)
    im = Image.new("RGB", (320, 200))
    px = im.load()
    for x in range(0, 320, 8):
        c = (r.randrange(256), r.randrange(256), r.randrange(256))
        for y in range(200):
            for dx in range(8):
                px[x + dx, y] = c
    b = io.BytesIO(); im.save(b, "JPEG"); return b.getvalue()


foto = tmp / "organizzate"
for f in ("hero", "galleria", "installazioni", "video"):
    (foto / f).mkdir(parents=True)
for i in range(6):
    (foto / "galleria" / f"galleria-0{i}.jpg").write_bytes(jpg(i))
(foto / "installazioni/installazione-01.jpg").write_bytes(jpg(50))
(foto / "hero/hero-01.jpg").write_bytes(jpg(60))
env = dict(os.environ, DATA_DIR=str(tmp / "data"), FOTO_DIR=str(foto), APP_MODE="production", ADMIN_PASSWORD="abcdefgh1234", SECRET_KEY="x" * 40, LMC_NO_BG="1")
# 6 «worker» che si avviano nello stesso istante sullo stesso database (come gunicorn --workers 2 al riavvio, ma peggio)
code = "from backend import create_app; create_app()"
init = subprocess.run([sys.executable, "-c", "import os; from backend.db import init_db; init_db()"], env=env, capture_output=True)
procs = [subprocess.Popen([sys.executable, "-c", code], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for _ in range(6)]
for p in procs:
    p.wait()
os.environ.update(env)
from backend import create_app
from backend.db import q, ex
app = create_app()
with app.app_context():
    rows = q("SELECT id,filename,source FROM media WHERE source LIKE 'cartella:%'")
    keys = [r["source"].split("#")[0] for r in rows]
    check("avvio simultaneo di 6 worker: ogni foto importata UNA sola volta", len(rows) == 8 and len(set(keys)) == 8)
    check("nessun file orfano in uploads", len({r['filename'] for r in rows}) == 8)
    # database già sporco (produzione): stessa foto inserita due volte
    r0 = rows[0]
    ex("INSERT INTO media(filename,kind,title,caption,category,show_home,show_gallery,show_intro,featured,sort,source) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
       ("copia_doppia", "image", "dup", "", "Eventi", 1, 1, 0, 0, 999, r0["source"]))
    ex("INSERT INTO media(filename,kind,title,caption,category,show_home,show_gallery,show_intro,featured,sort,source) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
       ("copia_vecchia", "image", "dup2", "", "Eventi", 1, 1, 0, 0, 998, r0["source"].split("#")[0] + "#vecchiohash"))
    from backend.foto_sync import sync
    done, _ = sync()
    rows2 = q("SELECT source FROM media WHERE source LIKE 'cartella:%'")
    check("sync ripulisce i doppioni già nel database", len(rows2) == 8 and any("doppione rimosso" in d for d in done))
    check("tiene la riga che corrisponde al file attuale", any(r["source"] == r0["source"] for r in rows2))
    check("risincronizzazione idempotente dopo la pulizia", sync() == ([], []))

    # didascalia corretta nel manifest: arriva anche sulle foto già in produzione, ma non sovrascrive quelle scritte a mano
    man = {"galleria/galleria-00.jpg": {"caption": "Foto uno"}, "galleria/galleria-01.jpg": {"caption": "Foto due"}}
    (foto / "_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    sync()
    ex("UPDATE media SET caption='Scritta dall''admin' WHERE source LIKE 'cartella:galleria/galleria-01.jpg#%'")
    man["galleria/galleria-00.jpg"] = {"caption": "Foto uno corretta", "prima": ["Foto uno"]}
    man["galleria/galleria-01.jpg"] = {"caption": "Foto due corretta", "prima": ["Foto due"]}
    (foto / "_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    done, _ = sync()
    c0 = q("SELECT caption,title FROM media WHERE source LIKE 'cartella:galleria/galleria-00.jpg#%'", one=True)
    c1 = q("SELECT caption FROM media WHERE source LIKE 'cartella:galleria/galleria-01.jpg#%'", one=True)
    check("manifest: didascalia aggiornata sulle foto già pubblicate (anche il titolo)", c0["caption"] == "Foto uno corretta" and c0["title"] == "Foto uno corretta")
    check("manifest: la didascalia scritta a mano dall'admin non viene sovrascritta", c1["caption"] == "Scritta dall'admin")
    check("manifest: idempotente", sync() == ([], []))

# ---- cartella foto del repository: nessun doppione (byte identici o quasi identici) ----
from backend.controllo_foto import analizza
rep = analizza(Path("foto/organizzate"))
check("repository: nessuna foto identica (byte)", not rep["identiche"])
check("repository: nessuna foto quasi identica (stesso scatto)", not rep["simili"])
check("repository: nessuna didascalia ripetuta", not rep["didascalie_doppie"])
check("repository: ogni foto ha la sua voce nel manifest e viceversa", not rep["senza_manifest"] and not rep["manifest_orfano"])
check("repository: nessuna foto con orientamento EXIF da correggere", not rep["orientamento"])
check("repository: nessun video duplicato", not rep["video_doppi"])
# ---- home con le 25 foto + 6 video REALI del repository: ogni foto/video UNA sola volta (hero, card skill, galleria) ----
code = r"""
import re, json
from backend import create_app
h = create_app().test_client().get("/").get_data(as_text=True)
bs = lambda u: u.rsplit("_", 1)[0]
pf = re.findall(r'<a class="pf[^>]*href="([^"]+)"', h)
hs = re.findall(r'class="hs [^"]*" src="([^"]+)"', h)
sk = re.findall(r'class="skill-ph"><img[^>]*src="([^"]+)"', h)
vd = re.findall(r'data-src="(/media/[^"]+\.mp4)"', h)
caps = re.findall(r'<a class="pf[^>]*data-cap="([^"]*)"', h)
print(json.dumps(dict(pf=len(pf), hs=len(hs), sk=len(sk), uniche=len({bs(u) for u in pf + hs + sk}), vd=len(vd), vd_u=len(set(vd)), caps=len(caps), caps_u=len(set(caps)), demo="demo-tag" in h)))
"""
r = subprocess.run([sys.executable, "-c", code], env=dict(env, DATA_DIR=str(tmp / "data_reale"), FOTO_DIR=str(Path("foto/organizzate").resolve())), capture_output=True, text=True)
d = json.loads(r.stdout.strip().splitlines()[-1])
check(f"home reale: 25 foto = {d['hs']} hero + {d['sk']} card + {d['pf']} galleria, tutte diverse", d["pf"] + d["hs"] + d["sk"] == 25 and d["uniche"] == 25)
check("home reale: 6 video, nessuno ripetuto", d["vd"] == 6 and d["vd_u"] == 6)
check("home reale: didascalie della galleria tutte diverse, nessun bollino DEMO", d["caps"] == d["caps_u"] and not d["demo"])
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
