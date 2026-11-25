"""Toglie UNA scena da un video fatto con make_video.py (immagini e audio), tenendo tutto il resto com'è.
Uso:  python video/taglia_scena.py video/tutorial_clienti_orizzontale.mp4 4      (toglie la 4ª scena)
Le scene si riconoscono dalle dissolvenze al nero; l'audio (voce + musica) viene tagliato con due brevi dissolvenze."""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_video import segmenti, run, FPS


def main(path, n):
    path = Path(path)
    dur = segmenti(path)
    assert 1 <= n <= len(dur), f"il video ha {len(dur)} scene"
    a = sum(dur[:n - 1])
    b = a + dur[n - 1]
    a, b = round(a * FPS) / FPS, round(b * FPS) / FPS
    tot = sum(dur)
    out = Path(tempfile.mkdtemp(prefix="lmccut_")) / "out.mp4"
    fc = (f"[0:v]trim=0:{a},setpts=PTS-STARTPTS[v1];[0:v]trim={b}:{tot + 1},setpts=PTS-STARTPTS[v2];[v1][v2]concat=n=2:v=1:a=0[v];"
          f"[0:a]atrim=0:{a},asetpts=PTS-STARTPTS,afade=t=out:st={a - 0.15:.2f}:d=0.15[a1];"
          f"[0:a]atrim={b}:{tot + 1},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.15[a2];[a1][a2]concat=n=2:v=0:a=1[a]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)])
    out.replace(path)
    print(f"tolta la scena {n} ({a:.2f}-{b:.2f} s) da {path.name}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
