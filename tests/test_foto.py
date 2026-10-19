"""Test importatore social + sincronizzazione cartelle: python -m tests.test_foto"""
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
from PIL import Image

tmp = Path(tempfile.mkdtemp(prefix="lmc_foto_"))
os.environ["DATA_DIR"] = str(tmp / "data")
os.environ["FOTO_DIR"] = str(tmp / "organizzate")
os.environ.setdefault("ADMIN_PASSWORD", "TestLocale123")
import importa_social
from backend import create_app

ok = fail = 0


def check(name, cond):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name)
    ok, fail = ok + bool(cond), fail + (not cond)


def jpg(w, h, c):
    b = io.BytesIO()
    Image.new("RGB", (w, h), c).save(b, "JPEG")
    return b.getvalue()


zp = tmp / "ig.zip"
posts = [{"media": [{"uri": "media/posts/202403/a.jpg", "creation_timestamp": 1710000000, "title": "Installazione palco"}]},
         {"media": [{"uri": "media/posts/202404/b.jpg", "creation_timestamp": 1712000000, "title": "Serata"}]},
         {"media": [{"uri": "media/posts/202405/c.jpg", "creation_timestamp": 1713000000, "title": "Altra serata"}]}]
with zipfile.ZipFile(zp, "w") as z:
    z.writestr("content/posts_1.json", json.dumps(posts))
    z.writestr("media/posts/202403/a.jpg", jpg(1200, 900, (200, 0, 0)))
    z.writestr("media/posts/202404/b.jpg", jpg(2400, 1200, (0, 200, 0)))
    z.writestr("media/posts/202405/c.jpg", jpg(1000, 1000, (0, 0, 200)))
    z.writestr("your_instagram_activity/messages/inbox/x/photos/privata.jpg", jpg(1200, 900, (9, 9, 9)))
    z.writestr("media/reels/202407/r.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 200)

check("importatore ok", importa_social.main([str(zp), "--out", str(tmp / "organizzate"), "--hero", "1"]) == 0)
names = sorted(p.relative_to(tmp / "organizzate").as_posix() for p in (tmp / "organizzate").rglob("*.*"))
check("nomi ordinati", {"hero/hero-01.jpg", "installazioni/installazione-01.jpg", "galleria/galleria-01.jpg",
                        "video/video-01.mp4"} <= set(names))
check("messaggi privati esclusi", len(names) == 5)  # 4 media + manifest

# cartella semplice (WhatsApp/Drive): niente struttura Meta
plain = tmp / "plain"
(plain / "Allestimento Teatro").mkdir(parents=True)
(plain / "profile").mkdir()
for n, sz in [("IMG-20250316-WA0004.jpg", (1600, 1200)), ("IMG-20250317-WA0005.jpg", (2000, 1000)),
              ("IMG-20250320-WA0006.jpg", (1500, 1000)), ("IMG-20250321-WA0007.jpg", (1500, 1000)),
              ("Allestimento Teatro/img1.jpg", (1200, 900)), ("profile/serata.jpg", (1000, 1000))]:
    (plain / n).write_bytes(jpg(*sz, (n.__hash__() % 200, 20, 20)))
(plain / "VID-20250318-WA0001.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"1" * 300)
(plain / "iphone.HEIC").write_bytes(b"x" * 50)
out2 = tmp / "out2"
check("cartella semplice ok", importa_social.main([str(plain), "--out", str(out2)]) == 0)
check("semplice: smistamento", (out2 / "installazioni/installazione-01.jpg").exists()
      and (out2 / "video/video-01.mp4").exists() and (out2 / "hero/hero-01.jpg").exists()
      and not (out2 / "hero/hero-02.jpg").exists() and len(list((out2 / "galleria").iterdir())) == 4)
check("semplice: HEIC non importato", not any(p.suffix.lower() == ".heic" for p in out2.rglob("*")))

app = create_app()
c = app.test_client()
home = c.get("/").get_data(as_text=True)
check("segnaposto nascosti", "[Segnaposto]" not in home and "FOTO IN ARRIVO" not in home)
check("filtro Installazioni presente", 'data-cat="Installazioni"' in home and 'data-cat="Luci"' not in home)
check("hero reale", 'class="hs kb0 on" src="/media/' in home and "logo-1600" not in home.split('id="heroSlides"')[1].split("hero-shade")[0])
check("sezione skill con 5 foto", home.count('class="skill reveal"') == 5 and home.count('class="skill-ph"><img') == 5)
check("hero con slide dalle cartelle", home.count('class="hs ') >= 2)
check("intro cinematografica con 7 passi", home.count('class="slide kb') == 7 and 'id="introData"' in home and "Entra nello show" not in home)
js = open("app/static/js/site.js", encoding="utf-8").read()
check("nessuna voce sintetica del browser", "speechSynthesis" not in js and "SpeechSynthesisUtterance" not in js and "Risposta vocale" not in home)
check("font locali, niente CDN", "/static/fonts/playfair-display" in home and "googleapis" not in home)
check("sezione contatti con CTA preventivo", 'id="contatti"' in home and 'class="btn btn-night" href="#preventivo">Richiedi un preventivo' in home)
check("footer con rivedi intro e privacy", "Rivedi l'intro" in home and 'href="/privacy"' in home)
check("un solo h1", home.count("<h1") == 1)
check("voce.mp3 presente e collegata con i cue", '"voce":"/static/media/voce.mp3"' in home.replace(" ", "") and '"cues":[0.0' in home.replace(" ", ""))
check("audio nel DOM (musica + voce)", 'id="introMusic"' in home and 'id="introVoce"' in home)
check("video reale", 'class="lazyvid"' in home and "/static/media/loop1.mp4" not in home)
from backend.foto_sync import sync
with app.app_context():
    check("risincronizzazione idempotente", sync() == ([], []))
# sostituzione "stesso nome": la foto nuova prende il posto della vecchia (anche come hero)
hero_file = tmp / "organizzate" / "hero" / "hero-01.jpg"
with app.app_context():
    from backend.db import q
    old = q("SELECT filename FROM media WHERE featured=1", one=True)["filename"]
    hero_file.write_bytes(jpg(1800, 900, (1, 2, 3)))
    done, _ = sync()
    rows = q("SELECT filename,featured FROM media WHERE source LIKE 'cartella:hero/hero-01.jpg#%'")
    check("sostituzione stesso nome", len(done) == 1 and len(rows) == 1 and rows[0]["filename"] != old and rows[0]["featured"] == 1)
    check("vecchia foto rimossa", not list((tmp / "data" / "uploads").glob(f"{old}*")))
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
