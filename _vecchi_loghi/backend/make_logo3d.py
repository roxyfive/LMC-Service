"""Rende il logo circolare LMC Service in 3D realistico (mappa di altezze + illuminazione con materiali).

Uso (strumento di sviluppo, non serve per far girare il sito):
    pip install numpy pillow scipy fonttools brotli
    python -m backend.make_logo3d

Tecnica: ogni elemento (anello dorato con spessore, antenna parabolica metallica, lettere in rilievo...) è una mappa di
altezze 2.5D. Dalle altezze si ricavano le normali; ogni materiale (oro, acciaio, smalto nero, avorio) riflette un ambiente
da studio procedurale con luce radente da sinistra-alto, occlusione ambientale e ombre portate. Uscite in app/static/img/:
logo-3d-1024.png (principale), logo-3d-512.webp/-256.webp, icon-192/512.png, favicon.ico/png, logo-mono-white.svg.
"""
import math
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

from .config import ROOT

IMG = ROOT / "app" / "static" / "img"
FONTS = ROOT / "app" / "static" / "fonts"
N = 2048                  # lato della tela di rendering (px)
W = 270.0                 # lato della tela in unità del disegno (il logo è un cerchio di raggio 116 al centro)
K = N / W
CX = CY = W / 2


def font_ttf(name):
    from fontTools.ttLib import TTFont
    f = TTFont(str(FONTS / name))
    f.flavor = None
    p = Path(tempfile.gettempdir()) / (name + ".ttf")
    f.save(str(p))
    return str(p)


def grid():
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    return (x / K - CX), (y / K - CY)        # coordinate in unità del disegno, origine al centro


X, Y = grid()
R = np.hypot(X, Y)


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def aa(d, w=0.6):
    """Maschera antialias da distanza con segno (d<0 dentro) in unità del disegno."""
    return np.clip(0.5 - d / (w / K * 1.0 + 1e-9) * 0.0 - d * K * 0.8, 0, 1)


def blur(a, s):
    return ndi.gaussian_filter(a, s * K)


def text_mask(txt, size, weight, cx, cy, fontfile, spacing=0.0):
    img = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(fontfile, int(size * K))
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    widths = [d.textlength(c, font=f) for c in txt]
    total = sum(widths) + spacing * K * (len(txt) - 1)
    x0 = (CX + cx) * K - total / 2
    y0 = (CY + cy) * K
    for c, w in zip(txt, widths):
        d.text((x0, y0), c, font=f, fill=255, anchor="ls")
        x0 += w + spacing * K
    return np.asarray(img, np.float32) / 255


def arc_text(txt, size, weight, radius, fontfile, spacing_deg, center_deg=90):
    """Testo lungo un arco inferiore (leggibile dal basso verso l'alto sul cerchio), una lettera per volta."""
    f = ImageFont.truetype(fontfile, int(size * K))
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    ws = [probe.textlength(c, font=f) for c in txt]
    ang = [w / K / radius * 180 / math.pi + spacing_deg for w in ws]
    total = sum(ang) - spacing_deg
    a = center_deg + total / 2          # si parte da sinistra (angolo grande) e si va verso destra
    out = Image.new("L", (N, N), 0)
    for c, w, da in zip(txt, ws, ang):
        mid = a - da / 2 + spacing_deg / 2
        if c.strip():
            g = Image.new("L", (int(size * K * 2), int(size * K * 2)), 0)
            ImageDraw.Draw(g).text((g.width // 2, g.height // 2), c, font=f, fill=255, anchor="mm")
            g = g.rotate(-(90 - mid) * -1 + 0, resample=Image.BICUBIC)   # base della lettera verso il centro
            th = math.radians(mid)
            px = (CX + radius * math.cos(th)) * K - g.width / 2
            py = (CY + radius * math.sin(th)) * K - g.height / 2
            out.paste(g, (int(px), int(py)), g)
        a -= da
    return np.asarray(out, np.float32) / 255


def ellipse_coords(cx, cy, rx, ry, rot_deg):
    t = math.radians(rot_deg)
    dx, dy = X - cx, Y - cy
    u = dx * math.cos(t) + dy * math.sin(t)
    v = -dx * math.sin(t) + dy * math.cos(t)
    return u / rx, v / ry


def build():
    H = np.zeros((N, N), np.float32)
    M = np.zeros((N, N), np.uint8)          # materiale: 1 smalto, 2 oro, 3 acciaio, 4 avorio, 5 verde, 6 bianco, 7 rosso
    R0 = 104.0
    coin = (R <= R0 + 0.01).astype(np.float32)

    # smalto nero: leggera cupola
    inside = R < 99
    H = np.where(inside, 1.0 + 1.2 * (1 - (R / 99) ** 2), H)
    M[R <= R0] = 1

    # anello esterno dorato con sezione tondeggiante (spessore reale)
    rm, w = 100.5, 4.6
    t = np.clip((R - rm) / w, -1, 1)
    ring = np.sqrt(np.clip(1 - t * t, 0, 1))
    mring = (np.abs(R - rm) <= w)
    H = np.where(mring, 1.0 + 9.0 * ring, H)
    M[mring] = 2
    # filetto interno: sottile solco + cordoncino argentato
    g = np.abs(R - 94.5)
    fil = (g < 0.9)
    H = np.where(fil, 1.0 + 2.6 * np.sqrt(np.clip(1 - (g / 0.9) ** 2, 0, 1)), H)
    M[fil] = 4

    # icona originale: disco/oblo ovale inclinato + due bande curve parallele sotto (a mezzaluna)
    ANG, C0, RX0, RY0 = 43.0, (4.0, -40.0), 41.0, 17.0
    ta = math.radians(ANG)
    vx, vy = -math.sin(ta), math.cos(ta)                 # perpendicolare: verso in basso a sinistra
    GAP = 1.7

    def rho_of(shift, rx, ry, grow=0.0):
        u, v = ellipse_coords(C0[0] + vx * shift, C0[1] + vy * shift, rx + grow, ry + grow, ANG)
        return np.hypot(u, v)

    bands = ((8.6, 39.0), (17.2, 31.0))
    for k, (shift, rx) in enumerate(bands):
        rho = rho_of(shift, rx, RY0)
        gshift, grx = (0.0, RX0) if k == 0 else bands[k - 1]
        g = rho_of(gshift, grx, RY0, GAP)                  # ellisse precedente ingrandita = fessura
        mask = (rho <= 1.0) & (g > 1.0)
        edge = np.minimum((1 - rho) * RY0, (g - 1) * RY0)
        prof = np.sqrt(np.clip(edge / 1.8, 0, 1))
        H = np.where(mask, 2.0 + 4.0 + 2.2 * prof, H)
        M[mask] = 4
    rho = rho_of(0.0, RX0, RY0)
    disc = rho <= 1.0
    dome = np.sqrt(np.clip(1 - rho ** 2, 0, 1))
    H = np.where(disc, 2.0 + 5.0 + 3.0 * dome ** 0.35, H)
    M[disc] = 4

    # scritta LMC (avorio lucido) in rilievo
    pf = font_ttf("playfair-display-latin-wght-normal.woff2")
    it = font_ttf("inter-latin-wght-normal.woff2")
    lmc = text_mask("LMC", 40, 650, 0, 33, pf, spacing=3.2)
    lm = blur(lmc, 0.55)
    H = np.where(lm > 0.4, 2.0 + 7.0 * np.sqrt(np.clip((lm - 0.4) / 0.6, 0, 1)) + 1.0, H)
    M[lmc > 0.5] = 4
    # SERVICE in oro
    sv = text_mask("SERVICE", 11.5, 650, 0, 52.5, it, spacing=4.2)
    sm = blur(sv, 0.28)
    H = np.where(sm > 0.4, 2.0 + 3.6 * np.sqrt(np.clip((sm - 0.4) / 0.6, 0, 1)) + .6, H)
    M[sv > 0.5] = 2
    # filetti dorati ai lati di SERVICE
    for x0, x1 in ((-52, -33), (33, 52)):
        m = (np.abs(Y - 46.3) < 0.55) & (X > x0) & (X < x1)
        H = np.where(m, 3.0 + 1.2 * np.sqrt(np.clip(1 - ((Y - 46.3) / 0.55) ** 2, 0, 1)), H)
        M[m] = 2
    # tricolore smaltato
    for k, (x0, mat) in enumerate(((-12, 5), (-4, 6), (4, 7))):
        m = (X >= x0 + 0.2) & (X < x0 + 7.8) & (np.abs(Y - 59) < 1.5)
        H = np.where(m, 2.6, H)
        M[m] = mat
    # AUDIO · VIDEO · LUCI lungo l'arco inferiore
    arc = arc_text("AUDIO · VIDEO · LUCI", 7.6, 650, 83.0, it, 2.3)
    am = blur(arc, 0.18)
    H = np.where(am > 0.4, 2.0 + 2.2 * np.sqrt(np.clip((am - 0.4) / 0.6, 0, 1)) + .5, H)
    M[arc > 0.5] = 4

    H = np.where(coin > 0, H, 0).astype(np.float32)
    M = np.where(coin > 0, M, 0).astype(np.uint8)
    return H, M, coin


def env(rx, ry, rz, tint):
    """Ambiente da studio procedurale: cielo luminoso in alto, pavimento scuro, due softbox e un riflesso radente."""
    up = np.clip(ry * -1.0, -1, 1)                       # y negativo = verso l'alto nello schermo
    sky = 0.28 + 0.62 * smooth((up + 0.15) / 1.15)
    floor = 0.06 + 0.12 * smooth((up + 1) / 0.85)
    base = np.where(up > -0.05, sky, floor)
    sb1 = smooth(1 - np.hypot(rx + 0.55, ry + 0.62) / 0.38) * 1.6          # softbox principale alto-sinistra
    sb2 = smooth(1 - np.hypot(rx - 0.72, ry - 0.05) / 0.30) * 0.9          # softbox di riempimento a destra
    strip = smooth(1 - np.abs(ry + 0.18) / 0.05) * 0.55 * smooth((rx + 1) / 1.2)   # striscia orizzontale
    horizon = smooth(1 - np.abs(ry - 0.28) / 0.04) * 0.35
    e = base + sb1 + sb2 + strip + horizon
    return e[..., None] * np.asarray(tint, np.float32)[None, None, :]


def render(H, M, coin):
    Hs = ndi.gaussian_filter(H, 0.55 * K / 4)                    # leggero smussamento dei bordi
    gy, gx = np.gradient(Hs)
    s = 0.9 * K                                                   # intensità del rilievo (gradiente per unità di disegno)
    nx, ny, nz = -gx * s, -gy * s, np.ones_like(Hs)
    nl = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / nl, ny / nl, nz / nl

    L = np.array([-0.55, -0.62, 0.56], np.float32); L /= np.linalg.norm(L)          # luce principale (alto-sinistra)
    G = np.array([-0.93, -0.30, 0.20], np.float32); G /= np.linalg.norm(G)          # luce radente
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    graz = np.clip(nx * G[0] + ny * G[1] + nz * G[2], 0, 1)
    Hh = (L + np.array([0, 0, 1.0])) / np.linalg.norm(L + np.array([0, 0, 1.0]))
    nh = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1)
    # riflessione dell'ambiente
    rx, ry, rz = 2 * nz * nx, 2 * nz * ny, 2 * nz * nz - 1
    fres = 0.04 + 0.96 * (1 - nz) ** 4

    # occlusione ambientale + ombra portata sullo smalto
    ao = np.clip(1 - 0.10 * (ndi.gaussian_filter(H, 3.0 * K / 4) - H), 0.45, 1)
    sh = ndi.shift((H > 4.0).astype(np.float32), (7 * K / 8, 6 * K / 8), order=1)
    sh = ndi.gaussian_filter(sh, 2.2 * K / 4) * (H < 4.0)

    img = np.zeros((N, N, 3), np.float32)
    def put(mask, color):
        img[mask] = color[mask]

    gold_t, steel_t, ivory_t = (1.0, 0.78, 0.36), (0.93, 0.95, 1.0), (1.0, 0.96, 0.86)
    # oro: riflesso ambientale tinto + lobo speculare stretto + luce radente
    gold = env(rx, ry, rz, gold_t) * (0.72 + 0.28 * diff[..., None]) + (nh ** 70)[..., None] * np.array([1, .9, .6]) * 0.9 + (graz ** 6)[..., None] * np.array([1, .85, .5]) * 0.42
    gold = gold * (0.55 + 0.45 * ao[..., None]) + fres[..., None] * 0.10
    # acciaio: ambiente quasi puro, contrasto elevato, striature radiali nel catino
    ang = np.arctan2(Y, X)
    brush = 0.94 + 0.06 * np.sin(ang * 90)
    steel = env(rx * 1.05, ry * 1.05, rz, steel_t) * 1.05 * brush[..., None] + (nh ** 140)[..., None] * 0.95 + (graz ** 5)[..., None] * 0.35
    steel = steel * (0.50 + 0.50 * ao[..., None])
    ivory = env(rx, ry, rz, ivory_t) * 1.05 * (0.65 + 0.35 * diff[..., None]) + 0.42 * np.array(ivory_t) * diff[..., None] + (nh ** 90)[..., None] * 0.9 + (graz ** 6)[..., None] * 0.35
    ivory = ivory * (0.55 + 0.45 * ao[..., None]) + 0.08
    base = np.array([0.030, 0.038, 0.060], np.float32)
    enam = base[None, None, :] * (0.6 + 0.9 * diff[..., None]) + env(rx, ry, rz, (0.45, 0.5, 0.65)) * 0.10 * fres[..., None] * 3 \
        + (nh ** 55)[..., None] * 0.22 + (R < 94.5)[..., None] * (0.016 * (1 - (R / 99) ** 2))[..., None] * np.array([1, 1.2, 1.7])
    enam = enam * (1 - 0.65 * sh[..., None]) * (0.55 + 0.45 * ao[..., None])
    def flat(c):
        c = np.array(c, np.float32)
        return c[None, None, :] * (0.55 + 0.6 * diff[..., None]) + (nh ** 60)[..., None] * 0.5

    out = enam.copy()
    for mid, col in ((2, gold), (3, steel), (4, ivory), (5, flat((0.10, 0.50, 0.20))), (6, flat((0.92, 0.92, 0.9))), (7, flat((0.66, 0.12, 0.10)))):
        m = (M == mid)[..., None]
        out = np.where(m, col, out)
    out = np.clip(out, 0, 4)
    out = out / (1 + 0.18 * out)              # morbida compressione delle alte luci
    out = np.clip(out * 1.12, 0, 1) ** (1 / 1.05)
    # antialias del bordo del disco + ombra portata del medaglione
    edge = np.clip((104.0 - R) * K * 0.8 + 0.5, 0, 1)
    shadow = ndi.shift((R <= 104.0).astype(np.float32), (9 * K / 4, 6 * K / 4), order=1)
    shadow = ndi.gaussian_filter(shadow, 6.5 * K / 4) * 0.55
    alpha = np.maximum(edge, shadow * (1 - edge))
    rgb = out * edge[..., None]                         # fuori dal disco solo l'ombra nera
    return np.dstack([rgb, alpha]).astype(np.float32)


def mono_svg():
    """Versione monocromatica bianca (trasparente) per sfondi scuri: footer, stampa, ricami."""
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="240" height="240" role="img" aria-label="LMC Service – La Music Company Service" fill="none" stroke="#fff">
  <circle cx="120" cy="120" r="110" stroke-width="3"/><circle cx="120" cy="120" r="103" stroke-width="1" stroke-opacity=".6"/>
  <defs>
    <mask id="g1" maskUnits="userSpaceOnUse" x="-80" y="-60" width="160" height="140"><rect x="-80" y="-60" width="160" height="140" fill="#fff"/><ellipse rx="46.1" ry="20.7" fill="#000"/></mask>
    <mask id="g2" maskUnits="userSpaceOnUse" x="-80" y="-60" width="160" height="140"><rect x="-80" y="-60" width="160" height="140" fill="#fff"/><ellipse cy="9.1" rx="43.9" ry="20.7" fill="#000"/></mask>
  </defs>
  <g transform="translate(124 78) rotate(43) scale(1.06)" fill="#fff" stroke="none">
    <ellipse rx="41" ry="17"/>
    <ellipse cy="8.6" rx="39" ry="17" mask="url(#g1)"/>
    <ellipse cy="17.2" rx="31" ry="17" mask="url(#g2)"/>
  </g>
  <text x="120" y="154" text-anchor="middle" font-family="Georgia,'Times New Roman',serif" font-weight="600" font-size="44" letter-spacing="5" fill="#fff" stroke="none">LMC</text>
  <path d="M52 167h22M166 167h22" stroke-width="1.4"/>
  <text x="120" y="172" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="600" font-size="12" letter-spacing="6.5" fill="#fff" stroke="none">SERVICE</text>
  <path d="M96 182h48" stroke-width="3"/>
  <path id="a" d="M42.1 165A90 90 0 0 0 197.9 165"/>
  <text font-family="Arial,Helvetica,sans-serif" font-size="8.6" font-weight="600" letter-spacing="3.2" fill="#fff" stroke="none"><textPath href="#a" startOffset="50%" text-anchor="middle">AUDIO · VIDEO · LUCI</textPath></text>
</svg>
'''


def main():
    H, M, coin = build()
    rgba = render(H, M, coin)
    full = Image.fromarray((rgba * 255 + .5).astype(np.uint8), "RGBA")
    # ritaglia i margini mantenendo l'ombra: il medaglione (r=104) occupa ~77% della tela
    pad = int((CX - 112) * K)
    full = full.crop((pad, pad, N - pad, N - pad))
    IMG.mkdir(parents=True, exist_ok=True)
    main_png = full.resize((1024, 1024), Image.LANCZOS)
    main_png.save(IMG / "logo-3d-1024.png", optimize=True)
    for s in (512, 256, 128):
        full.resize((s, s), Image.LANCZOS).save(IMG / f"logo-3d-{s}.webp", "WEBP", quality=90, method=6)
    # icone app: quadrato nero con il logo (sicuro per le maschere "maskable")
    for s in (192, 512):
        bg = Image.new("RGB", (s, s), (10, 13, 20))
        logo = full.resize((int(s * 0.84), int(s * 0.84)), Image.LANCZOS)
        bg.paste(logo, ((s - logo.width) // 2, (s - logo.height) // 2), logo)
        bg.save(IMG / f"icon-{s}.png", optimize=True)
    # favicon (senza ombra: solo medaglione)
    fav = full.resize((256, 256), Image.LANCZOS)
    fav.save(IMG / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    full.resize((64, 64), Image.LANCZOS).save(IMG / "favicon-64.png", optimize=True)
    (IMG / "logo-mono-white.svg").write_text(mono_svg(), encoding="utf-8")
    print("logo 3D ok:", [p.name for p in sorted(IMG.glob("logo-3d-*")) + sorted(IMG.glob("favicon*"))])


if __name__ == "__main__":
    main()
