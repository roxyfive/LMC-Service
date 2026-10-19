"""Genera loghi ottimizzati, icone PWA e musica originale (royalty-free, sintetizzata).
Uso: python -m backend.make_assets"""
import wave
import numpy as np
from PIL import Image
from .config import ROOT

IMG = ROOT / "app" / "static" / "img"
MED = ROOT / "app" / "static" / "media"


def logos():
    IMG.mkdir(parents=True, exist_ok=True)
    im = Image.open(ROOT / "logo" / "logo.png").convert("RGB")
    for w in (480, 1600):
        c = im.copy()
        c.thumbnail((w, w))
        c.save(IMG / f"logo-{w}.webp", "WEBP", quality=85)
    og = im.resize((1200, 630), Image.LANCZOS)
    og.save(IMG / "logo-1200.jpg", quality=85)
    # icona: disco audio a sinistra del logo, su fondo nero quadrato
    ic = im.crop((310, 400, 460, 560))
    for s in (192, 512):
        base = Image.new("RGB", (s, s), (10, 10, 10))
        t = ic.copy()
        t.thumbnail((int(s * 0.7), int(s * 0.7)), Image.LANCZOS)
        base.paste(t, ((s - t.width) // 2, (s - t.height) // 2))
        base.save(IMG / f"icon-{s}.png")
    ft = Image.open(ROOT / "logo" / "fivetech.png").convert("RGB")
    ft.thumbnail((160, 160))
    ft.save(IMG / "fivetech-160.webp", "WEBP", quality=85)


def music(sec=48, sr=44100):
    """Pad ambientale cinematografico + battito sub, interamente generato: nessun diritto d'autore."""
    MED.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0, sec, sec * sr, endpoint=False)
    chords = [(110.0, 164.81, 220.0, 261.63), (87.31, 130.81, 174.61, 220.0),
              (98.0, 146.83, 196.0, 246.94), (110.0, 164.81, 220.0, 277.18)]
    seg = sec / 8
    sig = np.zeros_like(t)
    for i in range(8):
        a, b = int(i * seg * sr), int((i + 1) * seg * sr)
        tt = t[a:b]
        env = np.minimum(1, np.minimum((tt - tt[0]) / 2.0, (tt[-1] - tt) / 2.0))
        for f in chords[i % 4]:
            for det in (-0.4, 0.4):
                sig[a:b] += env * np.sin(2 * np.pi * (f + det) * tt) * 0.06
    # pulsazione 72 bpm
    beat = (t * 72 / 60) % 1
    sig += np.sin(2 * np.pi * 55 * t) * np.exp(-beat * 7) * 0.35
    sig += np.sin(2 * np.pi * 440 * t) * np.exp(-((t * 36 / 60) % 1) * 12) * 0.02
    sig /= max(1e-6, np.abs(sig).max())
    sig *= 0.8
    # loop senza click: dissolvenza finale
    fade = int(sr * 1.5)
    sig[-fade:] *= np.linspace(1, 0, fade)
    sig[:fade] *= np.linspace(0, 1, fade)
    pcm = (sig * 32767).astype(np.int16)
    with wave.open(str(MED / "music.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    logos()
    music()
    print("asset ok")
