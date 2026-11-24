"""Genera tutte le versioni del logo LMC Service a partire da UN solo file: logo/lmcs-logo.png.
Uso:  python -m backend.make_logo_assets

Il logo è bianco pieno su fondo trasparente: va sempre messo su sfondo scuro.

Produce in app/static/img: logo-480/1600.webp (poster/hero), logo-1200.jpg (Open Graph), logo-completo.webp,
logo-emblema-128/256/512.webp + 1024.png, icon-192/512.png, icon-maskable-192/512.png, apple-touch-icon.png,
favicon.ico (16/32/48), favicon-32.png, favicon-64.png; e in logo/: lmcs-logo-documenti.png (ritagliato, per i PDF)."""
import math
import numpy as np
from PIL import Image, ImageFilter
from .config import ROOT

IMG = ROOT / "app" / "static" / "img"
SRC = ROOT / "logo" / "lmcs-logo.png"
NERO = (22, 22, 28)          # = sfondo e theme-color del sito (#16161c, tema nero)
EMBLEM_BOTTOM = 660          # nella tavola 1080x1350 il disco sta sopra questa riga, le scritte sotto


def _crop_alpha(im, box=None):
    im = im.crop(box) if box else im
    return im.crop(im.getchannel("A").getbbox())


def load():
    full = Image.open(SRC).convert("RGBA")
    lockup = _crop_alpha(full)
    emblem = _crop_alpha(full, (0, 0, full.width, EMBLEM_BOTTOM))
    return lockup, emblem


def thicken(im, r):
    """Ispessisce i contorni di r pixel (alfa + colore)."""
    if r <= 0:
        return im
    pad = r + 2
    cv = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    cv.paste(im, (pad, pad))
    k = 2 * r + 1
    a = cv.getchannel("A").filter(ImageFilter.MaxFilter(k))
    on_black = Image.new("RGB", cv.size, (0, 0, 0))
    on_black.paste(cv.convert("RGB"), mask=cv.getchannel("A"))
    out = on_black.filter(ImageFilter.MaxFilter(k)).convert("RGBA")
    out.putalpha(a)
    return out


def render(src, width, ref_width=None):
    """Ridimensiona a `width` px di larghezza; se è una riduzione forte ispessisce i tratti (ref_width = larghezza di riferimento)."""
    s = (ref_width or width) / src.width
    r = 0   # il logo è pieno (bianco): nessun ispessimento necessario
    t = thicken(src, r)
    h = round(t.height * width / t.width)
    return t.resize((width, h), Image.Resampling.LANCZOS)


def background(w, h):
    """Sfondo nero grafite con leggero chiarore al centro (tema nero del sito)."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w * 0.62)) ** 2 + ((y - h / 2) / (h * 0.75)) ** 2)
    k = np.clip(1 - d, 0, 1)[..., None] ** 1.6
    base = np.array((10, 10, 14), np.float32)
    mid = np.array((36, 36, 44), np.float32)
    arr = base + (mid - base) * k
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def scena(w, h, src, frac):
    """Logo `src` centrato su sfondo scuro, largo `frac` della tela."""
    bg = background(w, h)
    lg = render(src, int(w * frac))
    bg.paste(lg, ((w - lg.width) // 2, (h - lg.height) // 2), lg)
    return bg


def square(src, size, frac, flat=True, ref=None):
    """Quadrato size x size con il disco centrato (frac = quota occupata)."""
    lg = render(src, int(size * frac), ref)
    if lg.height > int(size * frac):          # il disco non è quadrato: limita anche l'altezza
        lg = lg.resize((round(lg.width * size * frac / lg.height), int(size * frac)), Image.Resampling.LANCZOS)
    cv = Image.new("RGB", (size, size), NERO) if flat else Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cv.paste(lg, ((size - lg.width) // 2, (size - lg.height) // 2), lg)
    return cv


def icona_con_scritte(size, w_testo, h_max, flat=True):
    """Quadrato con disco sopra e scritte «LA MUSIC COMPANY SERVICE · AUDIO · VIDEO · LUCI» sotto (icona dell'app).
    w_testo = larghezza delle scritte in quota di `size`; h_max = altezza massima del gruppo in quota di `size`."""
    full = Image.open(SRC).convert("RGBA")
    emb = _crop_alpha(full, (0, 0, full.width, EMBLEM_BOTTOM))
    txt = _crop_alpha(full, (0, EMBLEM_BOTTOM, full.width, full.height))
    tw = size * w_testo
    th = txt.height * tw / txt.width
    gap = size * 0.06
    eh = size * h_max - th - gap                      # altezza che resta al disco
    ew = min(eh * emb.width / emb.height, size * 0.5)
    eh = ew * emb.height / emb.width
    tot = eh + gap + th
    cv = Image.new("RGB", (size, size), NERO) if flat else Image.new("RGBA", (size, size), (0, 0, 0, 0))
    y = (size - tot) / 2
    e = emb.resize((round(ew), round(eh)), Image.Resampling.LANCZOS)
    t = txt.resize((round(tw), round(th)), Image.Resampling.LANCZOS)
    cv.paste(e, (round((size - e.width) / 2), round(y)), e)
    cv.paste(t, (round((size - t.width) / 2), round(y + eh + gap)), t)
    return cv


def scena_video():
    """Tavola 1672x941 per gli script video (sostituisce la vecchia foto del logo)."""
    lockup, _ = load()
    return scena(1672, 941, lockup, 0.6)


def generate():
    IMG.mkdir(parents=True, exist_ok=True)
    lockup, emblem = load()
    # poster / hero di riserva (16:9) e anteprima social
    for w, name in ((480, "logo-480.webp"), (1600, "logo-1600.webp")):
        scena(w, round(w * 9 / 16), lockup, 0.62).save(IMG / name, "WEBP", quality=88)
    scena(1200, 630, lockup, 0.66).save(IMG / "logo-1200.jpg", quality=90)
    # logo completo con trasparenza (per usi futuri su sfondi scuri)
    render(lockup, 1200).save(IMG / "logo-completo.webp", "WEBP", quality=92, method=6)
    # emblema (disco) trasparente: intestazione, intro, chat, footer
    for s in (128, 256, 512):
        square(emblem, s, 0.92, flat=False).save(IMG / f"logo-emblema-{s}.webp", "WEBP", quality=92, method=6)
    square(emblem, 1024, 0.92, flat=False).save(IMG / "logo-emblema-1024.png", optimize=True)
    # icona dell'app (PWA, Android, iPhone): disco + scritte. "maskable" tiene tutto dentro la zona sicura (80%)
    for sz in (192, 512):
        icona_con_scritte(sz, 0.84, 0.80).save(IMG / f"icon-{sz}.png", optimize=True)
        icona_con_scritte(sz, 0.58, 0.56).save(IMG / f"icon-maskable-{sz}.png", optimize=True)
    icona_con_scritte(180, 0.84, 0.80).save(IMG / "apple-touch-icon.png", optimize=True)
    # logo completo per l'intro (a sinistra, come prima): larghezza nativa del file sorgente
    render(lockup, 420).save(IMG / "logo-completo-420.webp", "WEBP", quality=92, method=6)
    # favicon (solo disco: a 16-64 px le scritte non si leggerebbero)
    for s in (32, 64):
        square(emblem, s, 0.88, ref=int(s * 0.88)).save(IMG / f"favicon-{s}.png", optimize=True)
    square(emblem, 64, 0.90, ref=24).save(IMG / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    # logo bianco ritagliato (senza margini) per i documenti: il PDF ha l'intestazione nera
    lockup.save(ROOT / "logo" / "lmcs-logo-documenti.png", optimize=True)


if __name__ == "__main__":
    generate()
    print("logo ok:", sorted(p.name for p in IMG.glob("*") if p.stem.startswith(("logo", "icon", "favicon", "apple"))))
