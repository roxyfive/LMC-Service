"""Genera i video con ffmpeg + Pillow + voce italiana di Windows (SAPI "Elsa").
Uso:  python video/make_video.py          (loop sito + intro 16:9 e 9:16 + tutorial)
Musica: app/static/media/music.mp3 (sintetizzata, royalty-free)."""
import json
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "video"
MEDIA = ROOT / "app" / "static" / "media"
LOGO = Image.open(ROOT / "logo" / "logo.png").convert("RGB")
FONT = "C:/Windows/Fonts/arialbd.ttf"
FPS = 25
RED = (225, 6, 0)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg errore:\n{r.stderr[-1500:]}")


def tts(lines, tmp):
    """Una WAV per riga con la voce italiana; ritorna lista di (path, durata)."""
    txt = tmp / "lines.txt"
    txt.write_text("\n".join(lines), encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Speech;$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          "$s.SelectVoice('Microsoft Elsa Desktop');$s.Rate=-1;$i=0;"
          f"Get-Content -Encoding UTF8 '{txt}' | ForEach-Object {{ $s.SetOutputToWaveFile('{tmp}\\v'+$i+'.wav');$s.Speak($_);$s.SetOutputToNull();$i++ }}")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)
    out = []
    for i in range(len(lines)):
        p = tmp / f"v{i}.wav"
        with wave.open(str(p)) as w:
            out.append((p, w.getnframes() / w.getframerate()))
    return out


def frame(w, h, text, idx, logo_big=False, sub=None):
    """Fotogramma statico 1.25x (per lo zoom): sfondo dal logo, fasci rossi, testo."""
    W, H = int(w * 1.25), int(h * 1.25)
    rnd = random.Random(idx * 11)
    lw, lh = LOGO.size
    crop_w = min(lw, int(lh * W / H))
    x0 = rnd.randint(0, lw - crop_w)
    bg = LOGO.crop((x0, 0, x0 + crop_w, lh)).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(6 if h > w else 1))
    im = ImageEnhance.Brightness(bg).enhance(0.55)
    if logo_big:
        lg = LOGO.copy()
        lg.thumbnail((int(W * 0.78), int(H * 0.5)), Image.LANCZOS)
        im.paste(lg, ((W - lg.width) // 2, int(H * 0.12)))
    d = ImageDraw.Draw(im)
    fs = int(W * (0.06 if h > w else 0.045))
    font = ImageFont.truetype(FONT, fs)
    rows, cur = [], ""
    for wd in text.split():
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=font) > W * 0.8 and cur:
            rows.append(cur)
            cur = wd
        else:
            cur = t
    rows.append(cur)
    y = int(H * (0.66 if logo_big else 0.45)) - len(rows) * fs // 2
    for r in rows:
        d.text((W // 2 + 3, y + 3), r, font=font, fill=(0, 0, 0), anchor="mt")
        d.text((W // 2, y), r, font=font, fill=(255, 255, 255), anchor="mt")
        y += int(fs * 1.25)
    if sub:
        d.text((W // 2, y + 10), sub, font=ImageFont.truetype(FONT, int(fs * 0.5)), fill=RED, anchor="mt")
    bw = int(W * 0.3)
    bx, by, bh = (W - bw) // 2, int(H * 0.93), max(6, H // 140)
    for k, col in enumerate(((0, 143, 60), (255, 255, 255), RED)):
        d.rectangle((bx + k * bw // 3, by, bx + (k + 1) * bw // 3, by + bh), fill=col)
    p = Path(tempfile.gettempdir()) / f"lmc_frame_{w}_{idx}.png"
    im.save(p)
    return p


def build(lines, name, w, h, music_vol=0.30, logo_first_last=True, sub_last=None):
    tmp = Path(tempfile.mkdtemp(prefix="lmcvid_"))
    voices = tts(lines, tmp)
    lst, vlist = [], []
    for i, ((vp, vd), line) in enumerate(zip(voices, lines)):
        d = max(3.0, vd + 0.9)
        big = logo_first_last and i in (0, len(lines) - 1)
        png = frame(w, h, line, i, logo_big=big, sub=(sub_last if i == len(lines) - 1 else None))
        seg = tmp / f"s{i}.mp4"
        n = int(d * FPS)
        zexpr = f"1+0.10*on/{n}" if i % 2 == 0 else f"1.10-0.10*on/{n}"
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-vf",
             f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={FPS},"
             f"fade=t=in:st=0:d=0.5,fade=t=out:st={d-0.5:.2f}:d=0.5,format=yuv420p",
             "-t", f"{d:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(seg)])
        lst.append(f"file '{seg.as_posix()}'")
        pad = tmp / f"p{i}.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vp), "-af", f"adelay=300|300,apad=whole_dur={d:.2f}",
             "-ar", "44100", "-ac", "2", str(pad)])
        vlist.append(f"file '{pad.as_posix()}'")
    (tmp / "v.txt").write_text("\n".join(lst))
    (tmp / "a.txt").write_text("\n".join(vlist))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "v.txt"), "-c", "copy", str(tmp / "video.mp4")])
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "a.txt"), "-c", "copy", str(tmp / "voce.wav")])
    out = OUT / f"{name}.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp / "video.mp4"), "-i", str(tmp / "voce.wav"),
         "-stream_loop", "-1", "-i", str(MEDIA / "music.mp3"), "-filter_complex",
         f"[2:a]volume={music_vol}[m];[1:a]volume=1.6[v];[v][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out)])
    print("creato", out.name)


def loops():
    """3 loop brevi (Ken Burns / pulsazione luci) per la sezione Show demo."""
    MEDIA.mkdir(parents=True, exist_ok=True)
    src = ROOT / "app" / "static" / "img" / "logo-1600.webp"
    n = 6 * FPS
    fx = [(f"1+0.12*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)", ""),
          (f"1.12-0.12*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)", ",hue=h=10*sin(2*PI*t/3)"),
          ("1.1", f"(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)", ",eq=brightness=0.05*sin(2*PI*t*1.5)")]
    for i, (z, x, y, extra) in enumerate(fx, 1):
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(src), "-vf",
             f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s=960x540:fps={FPS}{extra},format=yuv420p",
             "-t", "6", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-movflags", "+faststart", str(MEDIA / f"loop{i}.mp4")])
        print("creato loop", i)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    base = json.loads((ROOT / "contenuti" / "testi.json").read_text(encoding="utf-8"))
    loops()
    righe = base["intro_righe"]
    build(righe, "intro_orizzontale_1080p", 1920, 1080, sub_last="LMC SERVICE · NAPOLI")
    build(righe, "intro_verticale_1080p", 1080, 1920, sub_last="LMC SERVICE · NAPOLI")
    tutorial = ["Come prenotare con LMC Service.", "Apri il sito e scegli: prenota un appuntamento.",
                "Seleziona il giorno e l'orario libero, inserisci i tuoi dati e conferma.",
                "Ti arriva un'email con il link per modificare o annullare.",
                "Ti serve un preventivo? Compila la richiesta con evento, data, luogo e servizi.",
                "Hai domande? Scrivi o parla con l'assistente, attivo tutti i giorni a ogni ora.",
                "LMC Service. Audio, video, luci."]
    build(tutorial, "tutorial_clienti_orizzontale", 1920, 1080, sub_last="La Music Company Service")
