"""Miglioramento uniforme ed elegante di tutte le foto di foto/organizzate (hero, galleria, installazioni).

Su OGNI jpg/png applica, con intensità volutamente contenuta (nessun effetto «finto»):
  1. orientamento corretto dai dati EXIF;
  2. esposizione: punto di nero/bianco appena ripuliti e leggero recupero delle ombre nelle scene scure (gamma limitata);
  3. contrasto: curva ad S morbida applicata solo alla luminosità (i colori non virano);
  4. colore: bilanciamento del bianco molto prudente (±4 %) e vibranza lieve (i colori già saturi non si toccano);
  5. riduzione rumore: sfocatura dei soli canali colore + mediana leggera solo nelle ombre (i dettagli restano);
  6. nitidezza: maschera di contrasto leggera, solo sulla luminosità.

Gli originali non vengono persi: prima di sovrascrivere si copiano in foto/_originali/ (cartella locale, non versionata) e un registro
(`_enhanced.json`) ricorda quali file sono già stati migliorati, così rilanciare lo script NON applica il miglioramento due volte.

Uso:
    python -m backend.enhance_foto                     # migliora le foto non ancora migliorate
    python -m backend.enhance_foto --force             # rifà tutto partendo dagli originali in foto/_originali/
    python -m backend.enhance_foto --confronto DIR     # salva anche immagini «prima | dopo» in DIR
"""
import argparse
import hashlib
import json
import shutil
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

EXT = {".jpg", ".jpeg", ".png"}
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def _luma(a):
    return a @ LUMA


def enhance(im):
    """Ritorna (immagine migliorata, statistiche). `im` è una PIL.Image già orientata."""
    im = im.convert("RGB")
    a = np.asarray(im, np.float32) / 255.0
    y = _luma(a)
    before = dict(media=float(np.median(y)), p1=float(np.percentile(y, 1)), p99=float(np.percentile(y, 99)))

    # 1) livelli: ripulisce nero e bianco senza tagliare nulla di importante
    lo = min(before["p1"], 0.05) * 0.8
    hi = max(before["p99"], 0.90)
    a = np.clip((a - lo) / max(hi - lo, 1e-3), 0, 1)
    # recupero delle ombre nelle scene scure: gamma limitata (mai oltre 0.82), niente effetto «HDR»
    med = max(float(np.median(_luma(a))), 1e-3)
    g = float(np.clip(np.log(0.30) / np.log(med), 0.82, 1.0)) if med < 0.30 else 1.0
    a = a ** g

    # 3) contrasto: curva ad S morbida sulla sola luminosità (il rapporto è limitato per non gonfiare il rumore nel nero)
    y = _luma(a)
    ys = y * y * (3 - 2 * y)
    y2 = y * 0.78 + ys * 0.22
    ratio = np.clip((y2 + 1e-4) / (y + 1e-4), 0.7, 1.35)
    a = np.clip(a * ratio[..., None], 0, 1)

    # 4) colore: bilanciamento del bianco prudente + vibranza lieve
    mean = a.reshape(-1, 3).mean(0)
    gains = np.clip(mean.mean() / np.maximum(mean, 1e-3), 0.96, 1.04)
    a = np.clip(a * gains, 0, 1)
    y = _luma(a)
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    boost = 1.0 + 0.12 * (1.0 - sat)
    a = np.clip(y[..., None] + (a - y[..., None]) * boost[..., None], 0, 1)

    out = Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGB")

    # 5) rumore: solo colore + mediana leggera nelle ombre; 6) nitidezza solo sulla luminosità
    ycc = out.convert("YCbCr")
    Y, Cb, Cr = ycc.split()
    Cb = Cb.filter(ImageFilter.GaussianBlur(1.6))
    Cr = Cr.filter(ImageFilter.GaussianBlur(1.6))
    Yn = np.asarray(Y, np.float32) / 255
    med_y = np.asarray(Y.filter(ImageFilter.MedianFilter(3)), np.float32) / 255
    w = np.clip((0.35 - Yn) / 0.35, 0, 1) ** 2 * 0.55      # più forte nel nero profondo, nullo nelle luci
    Y = Image.fromarray(((Yn * (1 - w) + med_y * w) * 255 + 0.5).astype(np.uint8), "L")
    Y = Y.filter(ImageFilter.UnsharpMask(radius=1.1, percent=38, threshold=3))
    out = Image.merge("YCbCr", (Y, Cb, Cr)).convert("RGB")

    ya = _luma(np.asarray(out, np.float32) / 255)
    after = dict(media=float(np.median(ya)), p1=float(np.percentile(ya, 1)), p99=float(np.percentile(ya, 99)))
    return out, dict(prima=before, dopo=after, gamma=round(g, 3))


def _sha(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def run(cartella, originali, force=False, confronto=None, log=print):
    cartella, originali = Path(cartella), Path(originali)
    reg_path = cartella / "_enhanced.json"
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        reg = {}
    done, skipped = [], []
    files = sorted(p for p in cartella.rglob("*") if p.is_file() and p.suffix.lower() in EXT and not p.name.startswith((".", "_"))
                   and "_originali" not in p.parts)
    for p in files:
        rel = p.relative_to(cartella).as_posix()
        if not force and reg.get(rel) == _sha(p):
            skipped.append(rel)
            continue
        backup = originali / rel
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, backup)                       # l'originale resta salvo prima di sovrascrivere
        src = backup if force else p                       # con --force si riparte sempre dall'originale
        im = Image.open(BytesIO(src.read_bytes()))
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)                   # 1) orientamento corretto
        exif = im.getexif()
        exif[274] = 1
        out, st = enhance(im)
        out.save(p, "JPEG", quality=91, subsampling=0, optimize=True, progressive=True, icc_profile=icc, exif=exif.tobytes())
        reg[rel] = _sha(p)
        done.append(rel)
        log(f"  {rel}: luminosità media {st['prima']['media']:.2f} → {st['dopo']['media']:.2f} (gamma {st['gamma']})")
        if confronto:
            cdir = Path(confronto)
            cdir.mkdir(parents=True, exist_ok=True)
            a = ImageOps.exif_transpose(Image.open(BytesIO(backup.read_bytes()))).convert("RGB")
            b = out
            h = 900
            a2 = a.resize((int(a.width * h / a.height), h))
            b2 = b.resize((int(b.width * h / b.height), h))
            sheet = Image.new("RGB", (a2.width + b2.width + 12, h), "white")
            sheet.paste(a2, (0, 0))
            sheet.paste(b2, (a2.width + 12, 0))
            sheet.save(cdir / (rel.replace("/", "_").rsplit(".", 1)[0] + "_prima-dopo.jpg"), quality=88)
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return done, skipped


def main(argv=None):
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cartella", default=str(root / "foto" / "organizzate"))
    ap.add_argument("--originali", default=str(root / "foto" / "_originali"))
    ap.add_argument("--force", action="store_true", help="rifà tutto partendo dagli originali salvati")
    ap.add_argument("--confronto", help="cartella dove salvare le immagini «prima | dopo»")
    a = ap.parse_args(argv)
    done, skipped = run(a.cartella, a.originali, a.force, a.confronto)
    print(f"Migliorate {len(done)} foto, già migliorate (saltate) {len(skipped)}. Originali in {a.originali}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
