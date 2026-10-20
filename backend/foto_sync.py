"""Sincronizza foto/organizzate/ con il sito.

Cartelle: hero, galleria, installazioni, video. Ogni file nuovo viene ottimizzato e inserito nella
tabella `media` (idempotente: la colonna `source` ricorda cosa è già stato importato).
Uso manuale: `python -m backend.foto_sync`
"""
import hashlib
import json
import re
import shutil as _shutil
import subprocess
from pathlib import Path
import shutil
from io import BytesIO
from PIL import Image, ImageOps
from .config import FOTO_DIR, UPLOADS, MAX_VID
from .db import q, ex
from .media import save_image_obj, delete_files, _is_video
import secrets

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VID_EXT = {".mp4", ".mov", ".m4v"}
# cartella -> (tipo, categoria, show_home, show_gallery, show_intro)
FOLDERS = {
    "hero": ("image", "Eventi", 1, 0, 1),
    "galleria": ("image", "Eventi", 1, 1, 0),
    "installazioni": ("image", "Installazioni", 1, 1, 0),
    "video": ("video", "Show Demo", 0, 0, 0),
}


def _manifest():
    p = FOTO_DIR / "_manifest.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _title(path, folder, meta):
    cap = (meta.get("caption") or "").strip().splitlines()
    if cap and cap[0]:
        return cap[0][:60]
    orig = Path(meta.get("origine") or "").stem
    if orig and not re.search(r"^(img|vid|dsc|pxl|mov|whatsapp)|\d{6,}|^[0-9a-f-]{20,}$", orig, re.I):
        return orig.replace("-", " ").replace("_", " ").capitalize()[:60]  # nome file descrittivo dato da chi ha caricato
    return path.stem.replace("-", " ").replace("_", " ").capitalize()[:60]


def _poster_image(path):
    """Locandina di un video: file `nome.poster.jpg` accanto al video, altrimenti (se c'è ffmpeg) un fotogramma a 1,5 s."""
    pj = path.with_suffix(".poster.jpg")
    try:
        if pj.is_file():
            return ImageOps.exif_transpose(Image.open(pj)).convert("RGB")
        if _shutil.which("ffmpeg"):
            for ss in ("1.5", "0"):          # video molto brevi: se a 1,5 s non c'è nulla si ripiega sul primo fotogramma
                r = subprocess.run(["ffmpeg", "-v", "error", "-ss", ss, "-i", str(path), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                                   capture_output=True, timeout=60)
                if r.returncode == 0 and r.stdout:
                    return Image.open(BytesIO(r.stdout)).convert("RGB")
    except Exception:
        pass
    return None


def sync():
    """Importa i file nuovi. Ritorna (importati, saltati) come liste di messaggi."""
    done, skipped = [], []
    if not FOTO_DIR.is_dir():
        return done, skipped
    UPLOADS.mkdir(parents=True, exist_ok=True)
    manifest = _manifest()
    have = {r["source"] for r in q("SELECT source FROM media WHERE source LIKE 'cartella:%'")}
    sort = q("SELECT COALESCE(MAX(sort),0) m FROM media", one=True)["m"]
    hero_set = bool(q("SELECT 1 FROM media WHERE featured=1 AND placeholder=0 AND hidden=0", one=True))
    present = set()          # file presenti ora nelle cartelle (serve a togliere dal sito quelli cancellati o spostati)
    for folder, (kind, cat, home, gal, intro) in FOLDERS.items():
        d = FOTO_DIR / folder
        if not d.is_dir():
            continue
        for path in sorted(p for p in d.iterdir() if p.is_file() and not p.name.startswith((".", "_")) and not p.name.endswith(".poster.jpg")):
            present.add(f"{folder}/{path.name}")
            ext = path.suffix.lower()
            if ext not in (IMG_EXT if kind == "image" else VID_EXT):
                skipped.append(f"{folder}/{path.name}: formato non supportato")
                continue
            data = path.read_bytes()
            src = f"cartella:{folder}/{path.name}#{hashlib.sha1(data).hexdigest()[:12]}"
            if src in have:
                continue
            # stesso nome file ma contenuto diverso = foto sostituita: rimuove la vecchia, ne eredita posto e hero
            prefix = f"cartella:{folder}/{path.name}#"
            stale = q("SELECT id,filename,sort,featured FROM media WHERE substr(source,1,?)=?", (len(prefix), prefix))
            base = secrets.token_hex(16)
            try:
                if kind == "image":
                    im = ImageOps.exif_transpose(Image.open(BytesIO(data))).convert("RGB")
                    save_image_obj(im, base)
                else:
                    if len(data) > MAX_VID:
                        raise ValueError("video oltre 60 MB, comprimilo")
                    if not _is_video(data[:16]):
                        raise ValueError("non è un video valido")
                    (UPLOADS / f"{base}.mp4").write_bytes(data)
                    poster = _poster_image(path)
                    if poster is not None:
                        save_image_obj(poster, base)          # locandina: /media/<base>_960.webp
            except Exception as e:  # file rotto: si segnala e si prosegue
                skipped.append(f"{folder}/{path.name}: {e}")
                continue
            meta = manifest.get(f"{folder}/{path.name}", {})
            if stale:
                for r in stale:
                    delete_files(r["filename"])
                    ex("DELETE FROM media WHERE id=?", (r["id"],))
                feat = int(any(r["featured"] for r in stale))
                pos = stale[0]["sort"]
            else:
                feat = int(folder == "hero" and not hero_set)
                sort += 1
                pos = sort
            hero_set = hero_set or bool(feat)
            ex("""INSERT INTO media(filename,kind,title,caption,category,show_home,show_gallery,show_intro,featured,sort,source)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
               (base, kind, _title(path, folder, meta), (meta.get("caption") or "")[:300], cat,
                home, gal, intro, feat, pos, src))
            done.append(f"{folder}/{path.name}")
    # file cancellati o spostati dalle cartelle: spariscono anche dal sito (altrimenti restano foto «fantasma»).
    # Prudenza: si agisce solo se nelle cartelle c'è almeno un file (una cartella vuota per errore non svuota il sito).
    if present:
        for r in q("SELECT id,filename,source,featured FROM media WHERE source LIKE 'cartella:%'"):
            key = r["source"][len("cartella:"):].split("#")[0]
            if key not in present:
                delete_files(r["filename"])
                ex("DELETE FROM media WHERE id=?", (r["id"],))
                done.append(f"rimosso dal sito: {key}")
        if not q("SELECT 1 FROM media WHERE featured=1 AND placeholder=0 AND hidden=0 AND kind='image'", one=True):
            first = q("SELECT id FROM media WHERE source LIKE 'cartella:hero/%' AND hidden=0 AND kind='image' ORDER BY sort, id LIMIT 1", one=True)
            if first:
                ex("UPDATE media SET featured=1 WHERE id=?", (first["id"],))
    # locandine dei video già importati prima che esistessero (sito in produzione che si aggiorna con git pull)
    for r in q("SELECT filename,source FROM media WHERE kind='video' AND source LIKE 'cartella:video/%'"):
        if not (UPLOADS / f"{r['filename']}_960.webp").exists():
            key = r["source"][len("cartella:"):].split("#")[0]
            poster = _poster_image(FOTO_DIR / key)
            if poster is not None:
                save_image_obj(poster, r["filename"])
    if done:
        # con foto vere pubblicate i segnaposto non servono più
        ex("UPDATE media SET hidden=1, featured=0 WHERE placeholder=1")
        if not q("SELECT 1 FROM media WHERE kind='image' AND show_intro=1 AND hidden=0", one=True):
            ex("UPDATE media SET show_intro=1 WHERE kind='image' AND hidden=0 AND placeholder=0 AND id IN "
               "(SELECT id FROM media WHERE kind='image' AND hidden=0 AND placeholder=0 ORDER BY sort LIMIT 6)")
    return done, skipped


if __name__ == "__main__":
    from . import create_app
    with create_app().app_context():
        ok, ko = sync()
    print(f"Importati {len(ok)} file, saltati {len(ko)}")
    for m in ko:
        print("  -", m)
