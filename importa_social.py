#!/usr/bin/env python3
"""importa_social.py - estrae foto e video dall'esportazione dati di Instagram/Facebook.

    python importa_social.py instagram-export.zip [facebook-export.zip ...] [opzioni]

Funziona anche con una cartella (o ZIP di Drive/WhatsApp) di semplici jpg/mp4 SENZA struttura Meta:
in quel caso non applica i filtri Instagram/Facebook, ricava la data da EXIF o dal nome file
(IMG-20250316-WA0004.jpg) e legge nomi di file e sottocartelle come "didascalia"
(es. una cartella "Allestimento Teatro Mercadante" manda le foto in installazioni/).

Accetta uno o più ZIP (anche i "pezzi" 1/2/3 in cui Meta divide gli export grandi) oppure cartelle
già estratte. Estrae SOLO foto e video pubblicati (post, reel, album), li rinomina in ordine
(hero-01.jpg, galleria-01.jpg, installazione-01.jpg, video-01.mp4) e li copia in
foto/organizzate/{hero,galleria,installazioni,video}. I messaggi privati, gli sticker e le foto
profilo vengono ignorati e non vengono mai scritti su disco. Nessun file dello ZIP viene estratto
col suo nome originale (niente rischio "zip slip"). Solo libreria standard + Pillow.

Dopo l'importazione riavvia il sito (o Admin > Foto > Sincronizza): le foto vengono pubblicate.
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:  # senza Pillow si importa comunque, ma senza controllo delle dimensioni
    Image = None

ROOT = Path(__file__).resolve().parent
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VID_EXT = {".mp4", ".mov", ".m4v"}
# percorsi da non toccare mai (messaggi privati e simili)
BLOCK = re.compile(r"(^|/)(messages?|inbox|message_requests|stickers?|comments?|likes?|reactions?|ads?|"
                   r"shopping|avatars?|profile|profile_photos?|foto_del_profilo|archived_stories|recently_deleted|"
                   r"saved|search|security_and_login_information|contacts?)(/|_|$)", re.I)
STORIES = re.compile(r"(^|/)stor(y|ies)(/|_|$)", re.I)
ALLOW = re.compile(r"(^|/)(posts?|reels?|photos?|videos?|media|albums?|igtv|other|photos_and_videos|"
                   r"archived_posts|your_posts)(/|_|$)", re.I)
INSTALL_WORDS = ("installazion|allestiment|montaggio|montiamo|rigging|impiant|line ?array|led ?wall|ledwall|"
                 "struttur|truss|cablagg|set ?up|backstage|in allestimento|palco montato")
CHUNK = 1 << 20
MAX_MEMBER = 1 << 30  # 1 GB: oltre non è una foto/video di un evento


def fix_text(s):
    """Meta salva i JSON con UTF-8 letto come latin-1 ('Ã¨' al posto di 'è'): lo ripariamo."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


class Source:
    """Un ZIP o una cartella: elenca i file e li legge in streaming."""

    def __init__(self, path):
        self.path = Path(path)
        self.zf = None
        if self.path.is_dir():
            self.files = {}
            for p in self.path.rglob("*"):
                if p.is_file() and not p.is_symlink():
                    self.files[p.relative_to(self.path).as_posix()] = (p.stat().st_size, p.stat().st_mtime)
        else:
            try:
                self.zf = zipfile.ZipFile(self.path)
            except (zipfile.BadZipFile, OSError) as e:
                sys.exit(f"ERRORE: '{path}' non è uno ZIP valido ({e}). Se il download è stato interrotto, riscaricalo.")
            self.files = {}
            for i in self.zf.infolist():
                if i.is_dir() or i.flag_bits & 0x1:
                    continue
                try:
                    ts = datetime(*i.date_time).timestamp()
                except ValueError:
                    ts = 0
                self.files[i.filename.replace("\\", "/")] = (i.file_size, ts)
            if any(i.flag_bits & 0x1 for i in self.zf.infolist()):
                sys.exit(f"ERRORE: '{path}' è protetto da password: non è un export Meta standard.")

    def open(self, name):
        if self.zf:
            return self.zf.open(name)
        return open(self.path / name, "rb")

    def read(self, name):
        with self.open(name) as f:
            return f.read()


def sha1_stream(src, name):
    h = hashlib.sha1()
    with src.open(name) as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def collect_meta(sources, log):
    """Legge i JSON dell'export: ritorna {uri_normalizzato: {ts, caption}}."""
    meta = {}

    def walk(o, ctx):
        if isinstance(o, dict):
            c = ctx
            for k in ("title", "post", "description"):
                v = o.get(k)
                if isinstance(v, str) and v.strip():
                    c = fix_text(v.strip())
                    break
            uri = o.get("uri")
            if isinstance(uri, str) and Path(uri).suffix.lower() in IMG_EXT | VID_EXT:
                ts = o.get("creation_timestamp") or o.get("taken_timestamp") or ctx_ts.get("t")
                meta[uri.replace("\\", "/").lstrip("/").lower()] = {"ts": ts, "caption": c}
            if "timestamp" in o and isinstance(o["timestamp"], int):
                prev = ctx_ts.get("t")
                ctx_ts["t"] = o["timestamp"]
                for v in o.values():
                    walk(v, c)
                ctx_ts["t"] = prev
                return
            for v in o.values():
                walk(v, c)
        elif isinstance(o, list):
            for v in o:
                walk(v, ctx)

    ctx_ts = {}
    for s in sources:
        for name in s.files:
            if name.lower().endswith(".json") and not BLOCK.search(name):
                try:
                    walk(json.loads(s.read(name).decode("utf-8", "replace")), "")
                except (ValueError, KeyError):
                    log(f"  (JSON non leggibile, ignorato: {name})")
    return meta


def lookup(meta, tails, name):
    low = name.lower()
    if low in meta:
        return meta[low]
    for n in (3, 2, 1):  # il percorso nel JSON può avere un prefisso diverso da quello nello ZIP
        tail = "/".join(low.split("/")[-n:])
        for k in tails.get(tail, ()):
            if k.endswith(tail):
                return meta[k]
    return {}


def image_info(data):
    """(larghezza, altezza, timestamp EXIF o 0) oppure None se non è un'immagine leggibile."""
    if Image is None:
        return None
    try:
        raw = Image.open(BytesIO(data))
        ts = 0
        try:
            d = raw.getexif().get_ifd(0x8769).get(0x9003) or raw.getexif().get(0x0132)  # DateTimeOriginal / DateTime
            if d:
                ts = datetime.strptime(str(d)[:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            pass
        w, h = ImageOps.exif_transpose(raw).size
        return w, h, ts
    except Exception:
        return None


NAME_DATE = re.compile(r"(?<!\d)(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)")
JUNK = re.compile(r"(^|/)(__MACOSX|\.[^/]*|thumbs\.db|desktop\.ini|\.thumbnails)(/|$)", re.I)


def name_date(name):
    m = NAME_DATE.search(Path(name).name)
    if not m:
        return 0
    try:
        return datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0


def existing_state(out):
    """Cosa c'è già nelle cartelle di destinazione: hash (per non duplicare) e ultimo numero usato."""
    hashes, last = set(), {"hero": 0, "galleria": 0, "installazione": 0, "video": 0}
    folders = {"hero": "hero", "galleria": "galleria", "installazioni": "installazione", "video": "video"}
    for folder, prefix in folders.items():
        d = out / folder
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.is_file() and not p.name.startswith((".", "_")):
                h = hashlib.sha1()
                with p.open("rb") as f:
                    for b in iter(lambda: f.read(CHUNK), b""):
                        h.update(b)
                hashes.add(h.hexdigest())
                m = re.match(rf"{prefix}-(\d+)", p.name)
                if m:
                    last[prefix] = max(last[prefix], int(m.group(1)))
    return hashes, last


def main(argv=None):
    ap = argparse.ArgumentParser(description="Estrae foto e video da un export Instagram/Facebook (ZIP o cartella).")
    ap.add_argument("export", nargs="+", help="ZIP o cartelle: export Instagram/Facebook oppure semplici jpg/mp4 (WhatsApp, Drive)")
    ap.add_argument("--out", default=str(ROOT / "foto" / "organizzate"), help="cartella di destinazione")
    ap.add_argument("--hero", type=int, default=3, help="quante foto orizzontali grandi mettere in hero/ (default 3)")
    ap.add_argument("--con-storie", action="store_true", help="includi anche le storie (di solito escluse)")
    ap.add_argument("--min-px", type=int, default=600, help="scarta immagini con lato maggiore sotto questi pixel (default 600)")
    ap.add_argument("--parole-installazioni", default=INSTALL_WORDS,
                    help="regex: se la didascalia la contiene la foto va in installazioni/")
    ap.add_argument("--dry-run", action="store_true", help="mostra cosa farebbe senza copiare nulla")
    a = ap.parse_args(argv)
    log = print
    out = Path(a.out)
    sources = [Source(p) for p in a.export]
    inst_re = re.compile(a.parole_installazioni, re.I)

    log("Lettura delle didascalie e delle date…")
    meta = collect_meta(sources, log)
    tails = {}
    for k in meta:
        for n in (1, 2, 3):
            tails.setdefault("/".join(k.split("/")[-n:]), []).append(k)

    hashes, last = existing_state(out)
    seen, items, skipped = set(hashes), [], {"già presenti/duplicati": 0, "messaggi/profilo/sticker": 0,
                                           "storie": 0, "troppo piccole": 0, "formato non supportato": 0}
    unsupported = []
    for s in sources:
        # export Meta = contiene JSON con i metadati; altrimenti è una cartella "semplice" (WhatsApp, Drive, telefono)
        plain = not any(n.lower().endswith(".json") for n in s.files)
        if plain:
            log(f"'{s.path.name}': nessuna struttura Meta, la tratto come cartella di foto/video semplici.")
        for name, (size, mtime) in sorted(s.files.items()):
            ext = Path(name).suffix.lower()
            if ext not in IMG_EXT | VID_EXT:
                if ext in (".heic", ".heif", ".gif", ".avi", ".3gp", ".mkv"):
                    skipped["formato non supportato"] += 1
                    unsupported.append(name)
                continue
            if plain:
                if JUNK.search(name):
                    continue
            else:
                if BLOCK.search(name) or not ALLOW.search(name):
                    skipped["messaggi/profilo/sticker"] += 1
                    continue
                if STORIES.search(name) and not a.con_storie:
                    skipped["storie"] += 1
                    continue
            if size > MAX_MEMBER or size == 0:
                continue
            kind = "video" if ext in VID_EXT else "image"
            w = h = exif_ts = 0
            if kind == "image":
                info = image_info(s.read(name))
                if info is None:
                    skipped["formato non supportato"] += 1
                    unsupported.append(name)
                    continue
                w, h, exif_ts = info
                if max(w, h) < a.min_px:
                    skipped["troppo piccole"] += 1
                    continue
            digest = sha1_stream(s, name)
            if digest in seen:
                skipped["già presenti/duplicati"] += 1
                continue
            seen.add(digest)
            m = {} if plain else lookup(meta, tails, name)
            ts = m.get("ts") or exif_ts or name_date(name) or mtime or 0
            caption = (m.get("caption") or "")[:500]
            # testo su cui cercare le parole chiave: didascalia + sottocartelle + nome file
            text = f"{caption} {' '.join(Path(name).parent.parts[-3:])} {Path(name).stem}".replace("_", " ").replace("-", " ")
            items.append({"src": s, "name": name, "kind": kind, "ext": ".jpg" if ext == ".jpeg" else ext, "w": w, "h": h,
                          "ts": ts, "caption": caption, "text": text, "sha1": digest})

    # classificazione
    imgs = [i for i in items if i["kind"] == "image"]
    wide = sorted((i for i in imgs if i["w"] >= 1400 and i["w"] / max(i["h"], 1) >= 1.5),
                  key=lambda i: -(i["w"] * i["h"]))
    # al massimo 1 foto su 4 va in hero (restano visibili anche in galleria quelle migliori)
    need_hero = max(0, min(a.hero, max(1, len(imgs) // 4)) - last["hero"])
    if len(wide) < need_hero:  # poche panoramiche: ripiega sulle foto orizzontali più grandi
        extra = sorted((i for i in imgs if i not in wide and i["w"] >= 1000 and i["w"] / max(i["h"], 1) >= 1.2),
                       key=lambda i: -(i["w"] * i["h"]))
        wide += extra
    for i in wide[:need_hero]:
        i["dest"], i["prefix"] = "hero", "hero"
    for i in items:
        if "dest" in i:
            continue
        if i["kind"] == "video":
            i["dest"], i["prefix"] = "video", "video"
        elif inst_re.search(i["text"]):
            i["dest"], i["prefix"] = "installazioni", "installazione"
        else:
            i["dest"], i["prefix"] = "galleria", "galleria"

    # numerazione: la più recente è la 01 (continua dopo gli eventuali file già presenti)
    counters = dict(last)
    manifest_new = {}
    for i in sorted(items, key=lambda i: (-i["ts"], i["name"])):
        counters[i["prefix"]] += 1
        i["new"] = f"{i['prefix']}-{counters[i['prefix']]:02d}{i['ext']}"
        when = datetime.fromtimestamp(i["ts"], timezone.utc).strftime("%Y-%m-%d") if i["ts"] else ""
        manifest_new[f"{i['dest']}/{i['new']}"] = {"caption": i["caption"], "data": when, "origine": i["name"]}

    summary = {}
    for i in items:
        summary[i["dest"]] = summary.get(i["dest"], 0) + 1
    log("\nRisultato" + (" (PROVA, nessun file copiato)" if a.dry_run else "") + ":")
    for d in ("hero", "galleria", "installazioni", "video"):
        log(f"  {d:14s} {summary.get(d, 0):4d} file")
    for k, v in skipped.items():
        if v:
            log(f"  ignorati - {k}: {v}")
    if unsupported:
        log(f"  Non importabili (es. HEIC iPhone): {', '.join(unsupported[:8])}{' …' if len(unsupported) > 8 else ''}"
            "\n  -> fatti reinviare come JPG/MP4 (WhatsApp li converte già; da Drive scegli 'Più compatibile' su iPhone).")
    if not items:
        log("\nNessun file nuovo da importare. Controlla di aver scaricato l'export in formato JSON/HTML con foto e video inclusi.")
        return 0
    if a.dry_run:
        for i in sorted(items, key=lambda i: (i["dest"], i["new"])):
            log(f"  {i['dest']}/{i['new']}  <-  {i['name']}")
        return 0

    for i in items:
        dst = out / i["dest"] / i["new"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        with i["src"].open(i["name"]) as fi, dst.open("wb") as fo:
            for b in iter(lambda: fi.read(CHUNK), b""):
                fo.write(b)
    mf = out / "_manifest.json"
    try:
        old = json.loads(mf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    old.update(manifest_new)
    mf.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"\nCopiati {len(items)} file in {out}. Elenco con date e didascalie: {mf}")
    log("Ora riavvia il sito (python run.py) oppure Admin > Foto > Sincronizza.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
