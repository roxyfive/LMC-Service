"""Sostituisce il finale del video «La nostra storia» (medaglione con il vecchio logo) con una chiusura col logo nuovo.
Tiene tutto il video fino a 185,3 s (dissolvenza al nero), poi: sfondo nero con fasci rossi + logo nuovo + le ultime due frasi come sottotitoli,
e dissolvenza finale. L'audio (voce + musica) resta quello originale, intero.
Uso:  python video/fine_storia.py [video.mp4]      (di norma app/static/media/storia_lmc.mp4; la copia dell'originale va nella cartella temporanea)"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_video import LOGO, run          # LOGO = logo nuovo su nero con fasci rossi (1672x941)

TAGLIO = 185.8                                         # il video originale si ferma qui (dissolvenza 185,3-185,8)
FRASI = [(185.8, 187.95, "Ogni momento merita di essere ricordato."), (188.58, 191.19, "Ogni emozione merita di vivere per sempre.")]
W, H = 1280, 720
FONT = str(ROOT / "backend" / "kit_assets" / "fonts" / "Inter-Regular.ttf")


def didascalia(testo, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 17)
    d.text((W // 2 + 1, 621), testo, font=f, fill=(0, 0, 0, 200), anchor="mm")
    d.text((W // 2, 620), testo, font=f, fill=(255, 255, 255, 255), anchor="mm")
    im.save(path)


def main(video):
    video = Path(video)
    orig = Path(tempfile.gettempdir()) / (video.stem + "_originale.mp4")    # copia fuori dal progetto (l'originale resta anche nella cronologia git)
    if not orig.exists():
        shutil.copy2(video, orig)
    tot = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(orig)], capture_output=True, text=True).stdout)
    tmp = Path(tempfile.mkdtemp(prefix="lmcstoria_"))
    card = tmp / "card.png"
    LOGO.resize((1600, 900), Image.LANCZOS).save(card)
    caps = []
    for k, (a, b, t) in enumerate(FRASI):
        p = tmp / f"c{k}.png"
        didascalia(t, p)
        caps.append((p, a - TAGLIO, b - TAGLIO))
    dur = tot - TAGLIO
    n = int(dur * 30) + 1
    ins = ["-i", str(orig), "-loop", "1", "-i", str(card)]
    for p, _, _ in caps:
        ins += ["-loop", "1", "-i", str(p)]
    fc = (f"[0:v]trim=0:{TAGLIO},setpts=PTS-STARTPTS,fade=t=out:st={TAGLIO - 0.5}:d=0.5[a];"
          f"[1:v]zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps=30,trim=0:{dur:.3f},setpts=PTS-STARTPTS,"
          f"fade=t=in:st=0:d=0.6,fade=t=out:st={dur - 1.2:.2f}:d=1.2[b0];")
    cur = "b0"
    for k, (_, a, b) in enumerate(caps):
        fc += f"[{cur}][{k + 2}:v]overlay=enable='between(t,{a:.2f},{b:.2f})'[b{k + 1}];"
        cur = f"b{k + 1}"
    fc += f"[a][{cur}]concat=n=2:v=1:a=0[v]"
    out = tmp / "out.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "slow", "-crf", "25",
         "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "copy", "-movflags", "+faststart", "-shortest", str(out)])
    out.replace(video)
    print("finale sostituito:", video.name, f"({TAGLIO}-{tot:.1f} s); originale in {orig.name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "app" / "static" / "media" / "storia_lmc.mp4")
