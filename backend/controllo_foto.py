"""Controllo qualità di foto/organizzate: doppioni, foto buie o sfocate, orientamento EXIF, coerenza con _manifest.json.

Uso:  python -m backend.controllo_foto            (stampa il rapporto; esce con 1 se trova doppioni o incoerenze)
"""
import hashlib
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

IMG = {".jpg", ".jpeg", ".png", ".webp"}
VID = {".mp4", ".mov", ".m4v"}


def _sha(p):
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()


def _dhash(im, s=16):
    a = np.asarray(im.convert("L").resize((s + 1, s), Image.LANCZOS), np.float32)
    return (a[:, 1:] > a[:, :-1]).flatten()


def _luma_stats(im):
    a = np.asarray(im.convert("L").resize((640, int(640 * im.height / im.width))), np.float32) / 255
    return float(a.mean()), float(np.percentile(a, 95))


def _sharp(im):
    """Nitidezza: varianza del Laplaciano su una versione a 800 px di lato lungo (confrontabile tra foto di formato diverso)."""
    g = im.convert("L")
    g.thumbnail((800, 800))
    a = np.asarray(g, np.float32)
    lap = a[1:-1, 1:-1] * 4 - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    return float(lap.var())


def analizza(root, soglia_simili=24, buio=0.16, sfocata=60):
    root = Path(root)
    try:
        man = json.loads((root / "_manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        man = {}
    files = sorted(p for p in root.glob("*/*") if p.is_file() and not p.name.startswith((".", "_")) and not p.name.endswith(".poster.jpg"))
    rel = lambda p: p.relative_to(root).as_posix()
    imgs = [p for p in files if p.suffix.lower() in IMG]
    vids = [p for p in files if p.suffix.lower() in VID]
    rep = dict(n_foto=len(imgs), n_video=len(vids), identiche=[], simili=[], didascalie_doppie=[], senza_manifest=[], manifest_orfano=[],
               orientamento=[], video_doppi=[], buie=[], sfocate=[])
    by = {}
    for p in imgs + vids:
        by.setdefault(_sha(p), []).append(rel(p))
    rep["identiche"] = [v for v in by.values() if len(v) > 1 and not v[0].startswith("video/")]
    rep["video_doppi"] = [v for v in by.values() if len(v) > 1 and v[0].startswith("video/")]
    hs, info = {}, {}
    for p in imgs:
        with Image.open(p) as im0:
            ori = im0.getexif().get(274, 1)
            im = ImageOps.exif_transpose(im0).convert("RGB")
        if ori not in (1, None):
            rep["orientamento"].append((rel(p), ori))
        hs[rel(p)] = _dhash(im)
        info[rel(p)] = (_luma_stats(im), _sharp(im))
    names = list(hs)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = int((hs[a] != hs[b]).sum())
            if d <= soglia_simili:
                rep["simili"].append((d, a, b))
    for n, ((mean, p95), sharp) in info.items():
        if mean < buio:
            rep["buie"].append((n, round(mean, 3)))
        if sharp < sfocata:
            rep["sfocate"].append((n, round(sharp, 1)))
    caps = {}
    for k, v in man.items():
        caps.setdefault((v.get("caption") or "").strip().lower(), []).append(k)
    rep["didascalie_doppie"] = [v for c, v in caps.items() if c and len(v) > 1]
    rep["senza_manifest"] = [rel(p) for p in imgs + vids if rel(p) not in man]
    rep["manifest_orfano"] = [k for k in man if not (root / k).exists()]
    rep["metriche"] = {n: dict(luminosita=round(m[0], 3), nitidezza=round(s, 1)) for n, (m, s) in info.items()}
    return rep


def main(argv=None):
    root = Path(__file__).resolve().parent.parent / "foto" / "organizzate"
    rep = analizza(root)
    for k in ("identiche", "simili", "video_doppi", "didascalie_doppie", "senza_manifest", "manifest_orfano", "orientamento", "buie", "sfocate"):
        print(f"{k:18} {rep[k] if rep[k] else '—'}")
    print(f"{rep['n_foto']} foto, {rep['n_video']} video")
    return 1 if (rep["identiche"] or rep["simili"] or rep["video_doppi"] or rep["didascalie_doppie"] or rep["senza_manifest"] or rep["manifest_orfano"]) else 0


if __name__ == "__main__":
    sys.exit(main())
