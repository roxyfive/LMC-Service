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

app = create_app()
c = app.test_client()
home = c.get("/").get_data(as_text=True)
check("segnaposto nascosti", "[Segnaposto]" not in home and "FOTO IN ARRIVO" not in home)
check("filtro Installazioni presente", 'data-cat="Installazioni"' in home and 'data-cat="Luci"' not in home)
check("hero reale", "/static/img/logo-1600.webp\"\n       alt=\"La Music" not in home and 'class="hero-bg" src="/media/' in home)
check("video reale", 'class="lazyvid"' in home and "/static/media/loop1.mp4" not in home)
from backend.foto_sync import sync
with app.app_context():
    check("risincronizzazione idempotente", sync() == ([], []))
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
