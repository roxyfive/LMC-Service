"""Foto reali del cliente: miglioramento (enhance_foto), sincronizzazione sulla VPS, video in evidenza, email ovunque,
tema nero/rosso e intro. python -m tests.test_foto_reali"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

tmp = Path(tempfile.mkdtemp(prefix="lmc_reali_"))
os.environ["DATA_DIR"] = str(tmp / "data")
os.environ["FOTO_DIR"] = str(tmp / "organizzate")
os.environ["APP_MODE"] = "production"
os.environ.setdefault("ADMIN_PASSWORD", "TestLocale123")
os.environ.setdefault("SECRET_KEY", "x" * 40)
from backend import create_app
from backend import enhance_foto

ok = fail = 0


def check(name, cond):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name)
    ok, fail = ok + bool(cond), fail + (not cond)


def jpg(w, h, c, orient=None):
    im = Image.new("RGB", (w, h), c)
    b = io.BytesIO()
    if orient:
        ex = Image.Exif()
        ex[274] = orient
        im.save(b, "JPEG", exif=ex.tobytes())
    else:
        im.save(b, "JPEG")
    return b.getvalue()


foto = tmp / "organizzate"
for f in ("hero", "galleria", "installazioni", "video"):
    (foto / f).mkdir(parents=True)
(foto / "hero/hero-01.jpg").write_bytes(jpg(1600, 800, (40, 40, 60)))
(foto / "galleria/galleria-01.jpg").write_bytes(jpg(900, 1600, (90, 60, 50), orient=6))   # EXIF: ruotata di 90°
(foto / "installazioni/installazione-01.jpg").write_bytes(jpg(1200, 900, (30, 80, 40)))
(foto / "installazioni/installazione-02.jpg").write_bytes(jpg(1200, 900, (80, 80, 20)))

# ---- enhance_foto: orientamento, originali al sicuro, nessun doppio miglioramento ----
orig = tmp / "_originali"
done, skipped = enhance_foto.run(foto, orig, log=lambda *_: None)
check("enhance: tutte le foto migliorate", len(done) == 4 and not skipped)
check("enhance: originali salvati", (orig / "galleria/galleria-01.jpg").exists() and (orig / "hero/hero-01.jpg").exists())
im = Image.open(foto / "galleria/galleria-01.jpg")
check("enhance: orientamento EXIF applicato (900x1600 + rot.90 → 1600x900) e tag azzerato", im.size == (1600, 900) and im.getexif().get(274, 1) == 1)
before = (foto / "hero/hero-01.jpg").read_bytes()
done2, skipped2 = enhance_foto.run(foto, orig, log=lambda *_: None)
check("enhance: rilanciato non rielabora (idempotente)", not done2 and len(skipped2) == 4 and (foto / "hero/hero-01.jpg").read_bytes() == before)
a = Image.open(foto / "hero/hero-01.jpg").convert("RGB").getpixel((100, 100))
o = Image.open(orig / "hero/hero-01.jpg").convert("RGB").getpixel((100, 100))
check("enhance: miglioramento contenuto (nessuno stravolgimento dei colori)", max(abs(x - y) for x, y in zip(a, o)) < 60)

# ---- video veri (ffmpeg) + manifest ----
have_ffmpeg = shutil.which("ffmpeg")
if have_ffmpeg:
    for n in (1, 2):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=270x480:rate=10:duration=1", "-pix_fmt", "yuv420p",
                        str(foto / f"video/video-0{n}.mp4")], check=True)
    (foto / "video/video-01.poster.jpg").write_bytes(jpg(270, 480, (200, 0, 0)))
man = {"video/video-01.mp4": {"caption": "Reel America's Cup", "origine": "Reel"},
       "video/video-02.mp4": {"caption": "Light show in sala"},
       "installazioni/installazione-01.jpg": {"caption": "Palco allestito", "credito": "Merette Uiterwaal"},
       "installazioni/installazione-02.jpg": {"caption": "Mixer audio", "credito": "Merette Uiterwaal"},
       "galleria/galleria-01.jpg": {"caption": "Il tecnico", "credito": "Merette Uiterwaal"},
       "hero/hero-01.jpg": {"caption": "Castello", "credito": "Merette Uiterwaal"}}
(foto / "_manifest.json").write_text(json.dumps(man), encoding="utf-8")

app = create_app()
c = app.test_client()
from backend.foto_sync import sync
from backend.db import q, ex
with app.app_context():
    n_src = q("SELECT COUNT(*) n FROM media WHERE source LIKE 'cartella:%'", one=True)["n"]
    check("sync: foto importate dalla cartella", n_src >= 4)
    check("sync: idempotente", sync() == ([], []))
    # produzione + git pull: una foto spostata/eliminata sparisce dal sito, una nuova arriva
    (foto / "galleria/galleria-01.jpg").rename(foto / "installazioni/installazione-03.jpg")
    done, _ = sync()
    srcs = [r["source"] for r in q("SELECT source FROM media WHERE source LIKE 'cartella:%'")]
    check("sync: foto spostata → vecchia chiave rimossa, nuova pubblicata", not any("galleria/galleria-01.jpg" in s for s in srcs) and any("installazioni/installazione-03.jpg" in s for s in srcs))
    check("sync: nessun duplicato dopo lo spostamento", len(srcs) == len(set(s.split("#")[0] for s in srcs)))
    # cartella temporaneamente vuota (montaggio mancante, git in corso): NON cancella tutto il sito
    shutil.move(str(foto), str(tmp / "spostata"))
    foto.mkdir()
    for f in ("hero", "galleria", "installazioni", "video"):
        (foto / f).mkdir()
    sync()
    check("sync: cartella vuota non svuota il database", q("SELECT COUNT(*) n FROM media WHERE source LIKE 'cartella:%'", one=True)["n"] >= 4)
    shutil.rmtree(foto)
    shutil.move(str(tmp / "spostata"), str(foto))
    sync()
    if have_ffmpeg:
        vids = q("SELECT * FROM media WHERE source LIKE 'cartella:video/%' ORDER BY sort,id")
        check("video importati con locandina", len(vids) == 2 and all(list((tmp / "data" / "uploads").glob(f"{v['filename']}_960.webp")) for v in vids))

home = c.get("/").get_data(as_text=True)
check("nessun bollino DEMO con foto reali", "demo-tag" not in home and "[Segnaposto]" not in home and "Foto dimostrative" not in home)
check("badge «Modalità demo» assente in produzione", "Modalità demo" not in home)
if have_ffmpeg:
    check("Show demo: il reel America's Cup è il video in evidenza", "vid-feat" in home and home.index("Reel America&#39;s Cup") < home.index("Light show in sala") and "In evidenza" in home)
    check("Show demo: gli altri video si aprono al tocco", 'class="vid-play"' in home)
mail = "lamusiccompany.24@gmail.com"
check("email nel footer", f'class="foot-mail" href="mailto:{mail}"' in home)
check("email nella sezione Contatti e nel Team (Pasquale)", home.count(mail) >= 3)
with app.app_context():
    from backend import ai
    check("email nella conoscenza dell'assistente", mail in ai.knowledge())
    t = q("SELECT email FROM team WHERE name='Pasquale'", one=True)
    check("email precompilata nel Team (Pasquale)", t and t["email"] == mail)
    ex("UPDATE team SET email='' WHERE name='Pasquale'")
    ex("UPDATE settings SET value='' WHERE key='email'")
    from backend.seed import seed  # un sito già in produzione la riceve al riavvio (git pull + restart)
    seed()
    check("riavvio su DB esistente: email ripristinata in Team e Testi", q("SELECT email FROM team WHERE name='Pasquale'", one=True)["email"] == mail
          and q("SELECT value FROM settings WHERE key='email'", one=True)["value"] == mail)
lg = c.get("/admin/login").get_data(as_text=True)
tok = (re.search(r'name="csrf" content="([0-9a-f]+)"', lg) or re.search(r'name="csrf" value="([0-9a-f]+)"', lg)).group(1)
c.post("/admin/login", data={"csrf": tok, "username": "admin", "password": os.environ["ADMIN_PASSWORD"]})
adm = c.get("/admin/testi").get_data(as_text=True)
check("email precompilata nei Testi dell'admin", mail in adm)
check("credito fotografo nel footer", "Merette Uiterwaal" in home)

# ---- tema nero/rosso ----
css = open("app/static/css/site.css", encoding="utf-8").read()
tema = css.split("TEMA NERO")[1]
check("tema: sfondo nero e testi bianchi", "html,body{background:#16161c;color:#fff}" in tema)
check("tema: accento rosso al posto dell'oro", "--gold:#e11d14" in tema and "--red:#e11d14" in tema)
check("tema: skill e form con bordo rosso", ".skill{background:#1f1f26;border:1px solid var(--red)}" in tema and "border:1px solid var(--red)" in tema.split("input,select,textarea")[1][:260])
check("tema: pulsanti secondari con bordo rosso", ".btn-line" in tema and "border-color:var(--red)" in tema)
check("tema: tasto Emergenza resta rosso vivo", "#ff2d22" in tema and ".sos{" in tema)
check("tema: font Montserrat/Space Grotesk mantenuti", "Montserrat" in css and "Space Grotesk" in css)
intro_css = tema.split("INTRO")[1]
check("intro: sfondo nero, cornice e barre rosse, testi bianchi",
      ".intro{background:#16161c;color:#fff}" in intro_css and "rgba(225,29,20" in intro_css and ".intro-bars b{background:linear-gradient(90deg,#ff3a30,#e11d14)}" in intro_css and ".intro-cap{color:#fff" in intro_css)
check("intro: il blocco ricolorazione non tocca posizione/dimensioni",
      not re.search(r"[{;](bottom|left|right|top|width|height|font-size|animation-duration|margin|padding)\s*:", intro_css))
# ---- intro: una foto diversa per slide, abbinata al tema; tema grigio-nerastro (non nero puro) ----
import random
from backend import vetrina
man_real = json.load(open("foto/organizzate/_manifest.json", encoding="utf-8"))   # le 25 foto vere: didascalie reali
pool = []
for i, (k, v) in enumerate((k, v) for k, v in man_real.items() if not k.startswith("video")):
    pool.append(dict(id=i + 1, title=v["caption"], caption=v["caption"], source=f"cartella:{k}#x", filename=f"f{i}", placeholder=0))
seen_sets = set()
for seed in range(12):
    ph = vetrina.pick_intro_photos(pool, random.Random(seed))
    ids = [m["id"] for m in ph if m]
    assert len(ids) == len(set(ids)), seed
    seen_sets.add(tuple(ids))
check("intro: nessuna foto ripetuta in nessuna delle 12 estrazioni (25 foto reali)", len(pool) == 25)
check("intro: ogni visita può mostrare foto diverse (non sempre le stesse)", len(seen_sets) > 6)
check("intro: foto insufficienti → meno slide, mai ripetizioni", len([m for m in vetrina.pick_intro_photos(pool[:4], random.Random(1)) if m]) == 4)
for seed in range(12):
    one = vetrina.pick_intro_photos(pool, random.Random(seed))
    assert re.search(r"mixer|regia audio|fonico|microfon|cassa", vetrina._text(one[2])), (seed, vetrina._text(one[2]))
    assert re.search(r"palco|montaggio|struttur|allestit|rigging", vetrina._text(one[1])), (seed, vetrina._text(one[1]))
    assert re.search(r"barre led|riflettor|proiettor|mirror|giochi di luce|luci", vetrina._text(one[3])), (seed, vetrina._text(one[3]))
    assert vetrina.folder_of(one[0]) == "hero" and vetrina.folder_of(one[6]) == "hero"
check("intro: slide abbinate al tema (Audio→mixer/regia, Allestimenti→palco, Ledwall e luci→luci; prima e ultima da hero)", True)
hh = c.get("/").get_data(as_text=True)
srcs = re.findall(r'class="slide kb\d" alt="" (?:data-)?src="([^"]+)"', hh)
check("intro in pagina: una immagine diversa per slide", len(srcs) == len(set(srcs)) >= 4)
check("tema: sfondo grigio-nerastro #16161c, sezioni #1c1c22, mai #000 come sfondo", "--night:#16161c" in tema and ".band,.band:has(#richieste){background:#1c1c22" in tema and "background:#000;" not in tema.replace("background:#000;color", ""))
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
