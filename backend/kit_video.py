"""Video tutorial del kit: «Tour sito LMC» (clienti) e «Gestire il gestionale» (Pasquale).

Ogni video esce in due formati: verticale 9:16 (social) e orizzontale 16:9. Slide animate (zoom lento + dissolvenze) sugli screenshot veri,
sottotitoli incisi nel video, voce narrante (un mp3 per scena in kit_assets/audio/<id>.mp3) e musica di fondo abbassata.
Se manca l'mp3 di una scena il video funziona lo stesso: durata calcolata dal testo, solo sottotitoli e musica.
"""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = Path(__file__).resolve().parent
FONTS = BASE / "kit_assets" / "fonts"
AUDIO = BASE / "kit_assets" / "audio"
LOGO = BASE.parent / "logo" / "fivetech.png"
MUSICA = BASE.parent / "app" / "static" / "media" / "music.mp3"
FPS = 30
SCURO, SCURO2, ROSSO = (22, 22, 28), (13, 13, 17), (214, 40, 40)
FORMATI = {"verticale": (1080, 1920), "orizzontale": (1920, 1080)}


def font(nome, size):
    return ImageFont.truetype(str(FONTS / nome), size)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg/ffprobe non riuscito:\n" + " ".join(map(str, cmd))[:400] + "\n" + r.stderr[-1500:])
    return r.stdout


def durata(f):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]).strip())


def sfondo(w, h):
    img = Image.new("RGB", (w, h), SCURO)
    px = ImageDraw.Draw(img)
    for y in range(h):                                   # sfumatura verticale scuro -> quasi nero
        t = y / h
        px.line([(0, y), (w, y)], fill=tuple(int(SCURO[i] * (1 - t) + SCURO2[i] * t) for i in range(3)))
    return img


def logo_alto(img, titolo_scena=None):
    w, h = img.size
    d = ImageDraw.Draw(img)
    s = w / 1080 if w < h else h / 1080
    lg = Image.open(LOGO).convert("RGBA")
    lg.thumbnail((int(280 * s), int(110 * s)))
    img.paste(lg, (int(48 * s), int(36 * s)), lg)
    d.text((w - int(48 * s), int(76 * s)), "LMC SERVICE", font=font("Montserrat-ExtraBold.ttf", int(34 * s)), fill=(255, 255, 255), anchor="rm")
    d.rectangle([0, int(150 * s), w, int(156 * s)], fill=ROSSO)
    return s


def a_capo(testo, f, maxw, d):
    righe, cur = [], ""
    for parola in testo.split():
        prova = (cur + " " + parola).strip()
        if d.textlength(prova, font=f) <= maxw:
            cur = prova
        else:
            righe.append(cur)
            cur = parola
    if cur:
        righe.append(cur)
    return righe


def schermata(src, w, h, box):
    """Screenshot dentro un riquadro con bordo rosso e angoli arrotondati; ritorna (immagine, x, y)."""
    bx, by, bw, bh = box
    im = Image.open(src).convert("RGB")
    k = min(bw / im.width, bh / im.height)
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    r = 26
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width, im.height], r, fill=255)
    pad = 10
    cornice = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cornice)
    cd.rounded_rectangle([0, 0, cornice.width - 1, cornice.height - 1], r + pad, fill=ROSSO + (255,))
    cornice.paste(im, (pad, pad), mask)
    x = bx + (bw - cornice.width) // 2
    y = by + (bh - cornice.height) // 2
    return cornice, x, y


def frame_base(scena, formato, shots, qr=None, url=""):
    """Immagine di fondo (senza sottotitoli) di una scena."""
    w, h = FORMATI[formato]
    img = sfondo(w, h)
    s = logo_alto(img)
    d = ImageDraw.Draw(img)
    tipo = scena["slide"]
    verticale = formato == "verticale"
    if tipo.startswith("intro") or tipo.startswith("outro"):
        titolo = scena["titolo"]
        f_t = font("Montserrat-ExtraBold.ttf", int((96 if verticale else 110) * s))
        righe = a_capo(titolo.upper(), f_t, w - 160 * s, d)
        y = h * (0.28 if verticale else 0.24)
        for r in righe:
            d.text((w / 2, y), r, font=f_t, fill=(255, 255, 255), anchor="mm")
            y += 120 * s
        d.rectangle([w / 2 - 90 * s, y + 10 * s, w / 2 + 90 * s, y + 22 * s], fill=ROSSO)
        if tipo.startswith("outro") and qr is not None:
            side = int((620 if verticale else 400) * s)
            q = Image.open(qr).convert("RGB").resize((side, side), Image.NEAREST)
            qx, qy = int(w / 2 - side / 2), int(y + (90 if verticale else 60) * s)
            d.rounded_rectangle([qx - 30, qy - 30, qx + side + 30, qy + side + 30], 28, fill=(255, 255, 255))
            img.paste(q, (qx, qy))
            d.text((w / 2, qy + side + 80 * s), url, font=font("SpaceGrotesk-SemiBold.ttf", int(44 * s)), fill=(255, 255, 255), anchor="mm")
        else:
            sub = scena.get("sottotitolo", "La Music Company Service · Napoli")
            d.text((w / 2, y + 100 * s), sub, font=font("Inter-Regular.ttf", int(46 * s)), fill=(190, 190, 202), anchor="mm")
    else:
        # titolo della scena (chip) + screenshot
        chip_f = font("Montserrat-ExtraBold.ttf", int(46 * s))
        tw = d.textlength(scena["titolo"].upper(), font=chip_f)
        cx, cy = (w / 2 if verticale else 90 * s + tw / 2 + 30 * s), (230 * s if verticale else 205 * s)
        d.rounded_rectangle([cx - tw / 2 - 30 * s, cy - 42 * s, cx + tw / 2 + 30 * s, cy + 42 * s], 40 * s, fill=ROSSO)
        d.text((cx, cy), scena["titolo"].upper(), font=chip_f, fill=(255, 255, 255), anchor="mm")
        dev = "mobile" if verticale else "desktop"
        src = Path(shots) / f"{tipo}-{dev}.png"
        if src.exists():
            if verticale:
                box = (60, 330, w - 120, 1200)
            else:
                box = (80, 250, w - 160, 680)
            cornice, x, y = schermata(src, w, h, box)
            ombra = Image.new("RGBA", (cornice.width + 80, cornice.height + 80), (0, 0, 0, 0))
            ImageDraw.Draw(ombra).rounded_rectangle([40, 40, ombra.width - 40, ombra.height - 40], 40, fill=(0, 0, 0, 170))
            ombra = ombra.filter(ImageFilter.GaussianBlur(26))
            img.paste(ombra, (x - 40, y - 20), ombra)
            img.paste(cornice, (x, y), cornice)
    return img


def spezza(caption, dur):
    """Divide il testo in frasi brevi con i tempi (proporzionali alla lunghezza)."""
    parti = [p.strip() for p in re.split(r"(?<=[.!?:;])\s+|(?<=,)\s+", caption) if p.strip()]
    chunks, cur = [], ""
    for p in parti:                                      # ricompatta le frasi troppo corte, spezza quelle lunghe
        if len(cur) + len(p) < 46:
            cur = (cur + " " + p).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        while len(c) > 90:
            cut = c.rfind(" ", 0, 70)
            out.append(c[:cut])
            c = c[cut + 1:]
        out.append(c)
    tot = sum(len(c) for c in out) or 1
    t, res = 0.0, []
    for c in out:
        dd = dur * len(c) / tot
        res.append((c, t, t + dd))
        t += dd
    return res


def png_sottotitolo(testo, formato, out):
    w, h = FORMATI[formato]
    s = w / 1080 if formato == "verticale" else h / 1080
    f = font("Inter-Bold.ttf", int((50 if formato == "verticale" else 46) * s))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    righe = a_capo(testo, f, w * (0.84 if formato == "verticale" else 0.70), d)
    lh = int(f.size * 1.35)
    bh = lh * len(righe) + 44
    y0 = int(h * 0.84) - bh // 2 if formato == "verticale" else h - 70 - bh
    bw = max(d.textlength(r, font=f) for r in righe) + 80
    d.rounded_rectangle([w / 2 - bw / 2, y0, w / 2 + bw / 2, y0 + bh], 30, fill=(10, 10, 14, 215))
    for i, r in enumerate(righe):
        d.text((w / 2, y0 + 22 + lh * i + lh / 2), r, font=f, fill=(255, 255, 255, 255), anchor="mm")
    img.save(out)


def stima_durata(testo):
    return max(3.5, len(testo.split()) / 2.5)


def clip_scena(scena, formato, shots, tmp, qr, url):
    """Un mp4 per scena: zoom lento, sottotitoli a tempo, voce (se c'è l'mp3)."""
    w, h = FORMATI[formato]
    mp3 = AUDIO / f"{scena['id']}.mp3"
    voce = mp3.exists()
    d_voce = durata(mp3) if voce else stima_durata(scena["audio"])
    D = round(d_voce + 0.9, 2)                            # mezzo secondo di respiro prima e dopo
    base = Path(tmp) / f"{scena['id']}-{formato}-base.png"
    frame_base(scena, formato, shots, qr, url).save(base)
    inputs = ["-loop", "1", "-t", str(D), "-framerate", str(FPS), "-i", str(base)]
    filtri = [f"[0:v]scale={w * 2}:{h * 2},zoompan=z='min(zoom+0.00045,1.07)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps={FPS},format=yuv420p[v0]"]
    ultimo = "v0"
    for i, (testo, a, b) in enumerate(spezza(scena["caption"], d_voce), 1):
        cap = Path(tmp) / f"{scena['id']}-{formato}-c{i}.png"
        png_sottotitolo(testo, formato, cap)
        inputs += ["-loop", "1", "-t", str(D), "-framerate", str(FPS), "-i", str(cap)]
        filtri.append(f"[{ultimo}][{i}:v]overlay=0:0:enable='gte(t,{a + 0.45:.2f})*lt(t,{b + 0.45:.2f})'[v{i}]")
        ultimo = f"v{i}"
    filtri.append(f"[{ultimo}]fade=t=in:d=0.3,fade=t=out:st={D - 0.3:.2f}:d=0.3[vout]")
    out = Path(tmp) / f"{scena['id']}-{formato}.mp4"
    n = len(inputs) // 8
    if voce:
        inputs += ["-i", str(mp3)]
        filtri.append(f"[{n}:a]adelay=450|450,apad,aresample=44100,aformat=channel_layouts=stereo[aout]")
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        filtri.append(f"[{n}:a]anull[aout]")
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filtri), "-map", "[vout]", "-map", "[aout]", "-t", str(D),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(out)])
    return out, D


def crea_video(copione, formato, shots, out, qr, url, musica=None):
    """Monta tutte le scene del copione in un unico mp4. Ritorna (percorso, durata_secondi, scene_con_voce)."""
    tmp = tempfile.mkdtemp(prefix="lmc_video_")
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as ex:     # le scene sono indipendenti: si montano in parallelo, l'ordine resta quello del copione
            res = list(ex.map(lambda sc: clip_scena(sc, formato, shots, tmp, qr, url), copione["scene"]))
        clips = [c for c, _ in res]
        tot = sum(D for _, D in res)
        lista = Path(tmp) / "lista.txt"
        lista.write_text("".join(f"file '{c}'\n" for c in clips))
        muto = Path(tmp) / "muto.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(muto)])
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        m = Path(musica or MUSICA)
        if m.exists():
            run(["ffmpeg", "-y", "-v", "error", "-i", str(muto), "-stream_loop", "-1", "-i", str(m), "-filter_complex",
                 f"[1:a]volume=0.07,afade=t=in:d=1.5,afade=t=out:st={max(tot - 2.5, 0):.2f}:d=2.5[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
                 "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
        else:
            shutil.copy(muto, out)
        con_voce = sum((AUDIO / f"{s['id']}.mp3").exists() for s in copione["scene"])
        return Path(out), durata(out), con_voce
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def copioni():
    return json.loads((BASE / "kit_assets" / "copioni.json").read_text(encoding="utf-8"))
