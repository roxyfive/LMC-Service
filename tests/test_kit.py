"""Test del kit di consegna: python -m tests.test_kit
QR (leggibili, URL giusto), PDF (pagine, intestazione FiveTech e piè di pagina su OGNI pagina, indice cliccabile),
video (ffprobe: formato, durata, audio+video) su un mini-copione, e il comando unico `python -m backend.kit_consegna`."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


tmp = Path(tempfile.mkdtemp(prefix="lmc_kit_test_"))
shots = tmp / "shots"
shots.mkdir()
from backend import kit_testi, kit_video  # noqa: E402

# screenshot finti (colore pieno) per ogni immagine citata dalle guide e dai copioni: il test non deve dipendere da Chromium
nomi = {s["img"] for s in kit_testi.ADMIN + kit_testi.CLIENTE if s.get("img")}
cop = kit_video.copioni()
for k in ("tour", "gestionale"):
    for sc in cop[k]["scene"]:
        if sc["slide"].startswith(("sito-", "admin-")):
            nomi.add(sc["slide"] + "-desktop")
for n in nomi:
    for dev, size in (("desktop", (1366, 850)), ("mobile", (780, 1688))):
        Image.new("RGB", size, (40, 40, 52)).save(shots / f"{n.replace('desktop', dev)}.png")

out = tmp / "consegna"
r = subprocess.run([sys.executable, "-m", "backend.kit_consegna", "--out", str(out), "--shots", str(shots), "--solo-pdf", "--url", "https://esempio.test"],
                   cwd=ROOT, capture_output=True, text=True, timeout=300)
check("kit_consegna --solo-pdf termina senza errori", r.returncode == 0, r.stdout[-800:] + r.stderr[-800:])
for f in ("guide/Guida-Admin-LMC.pdf", "guide/Guida-Cliente-LMC.pdf", "qr/QR1-app-clienti.png", "qr/QR2-accesso-admin.png",
          "qr/QR1-app-clienti-semplice.png", "qr/QR2-accesso-admin-semplice.png", "LEGGIMI.txt"):
    check(f"esiste {f}", (out / f).exists() and (out / f).stat().st_size > 1000)

# ---- QR
try:
    import cv2
    det = cv2.QRCodeDetector()
    for f, atteso in (("QR1-app-clienti", "https://esempio.test"), ("QR2-accesso-admin", "https://esempio.test/admin/login"),
                      ("QR1-app-clienti-semplice", "https://esempio.test"), ("QR2-accesso-admin-semplice", "https://esempio.test/admin/login")):
        val = det.detectAndDecode(cv2.imread(str(out / "qr" / f"{f}.png")))[0]
        check(f"QR {f} si legge e punta a {atteso}", val == atteso, val)
except ImportError:
    print("SKIP lettura QR (opencv non installato)")
w, h = Image.open(out / "qr" / "QR1-app-clienti.png").size
check("QR da stampa ad alta risoluzione", w >= 2000 and h >= 2500, f"{w}x{h}")

# ---- PDF
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
for nome, titolo, min_sez in (("Guida-Admin-LMC", "Guida Admin LMC", 14), ("Guida-Cliente-LMC", "Guida Cliente LMC", 8)):
    pdf = out / "guide" / f"{nome}.pdf"
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    pagine = txt.split("\f")
    pagine = [p for p in pagine if p.strip()]
    check(f"{nome}: almeno {min_sez} pagine", len(pagine) >= min_sez, len(pagine))
    check(f"{nome}: piè di pagina (titolo, versione, data) su ogni pagina", all(titolo in p and "versione " + kit_testi.VERSIONE in p and re.search(r"\d\d/\d\d/\d{4}", p) for p in pagine))
    check(f"{nome}: intestazione LMC SERVICE su ogni pagina", all("LMC SERVICE" in p for p in pagine))
    check(f"{nome}: indice presente", "Indice" in txt)
    if PdfReader:
        rd = PdfReader(str(pdf))
        # logo FiveTech (immagine) nell'intestazione di ogni pagina
        check(f"{nome}: logo FiveTech su ogni pagina", all(len(p.images) >= 1 for p in rd.pages))
        link = sum(1 for a in (rd.pages[1].get("/Annots") or []) if a.get_object().get("/Subtype") == "/Link")
        check(f"{nome}: indice cliccabile ({link} link)", link >= min_sez)
        check(f"{nome}: segnalibri nel PDF", len(rd.outline) >= min_sez)
        dest = [a.get_object().get("/Dest") for a in (rd.pages[1].get("/Annots") or [])]
        check(f"{nome}: i link puntano a destinazioni esistenti", all(d is not None for d in dest))
    else:
        print("SKIP controlli di struttura PDF (pypdf non installato)")
adm = subprocess.run(["pdftotext", "-layout", str(out / "guide" / "Guida-Admin-LMC.pdf"), "-"], capture_output=True, text=True).stdout
for parola in ("Fatture", "Acconti", "Recensioni", "Galleria", "Tariffe", "Statistiche", "COLLABORATORE", "RICHIESTA", "SALDATO", "Specifiche tecniche", "QR 2"):
    check(f"Guida Admin cita «{parola}»", parola in adm)
check("Guida Admin: passi numerati e schemi ASCII", "+-----------+" in adm and re.search(r"^\s*1\s+\S", adm, re.M) is not None)
cli = subprocess.run(["pdftotext", "-layout", str(out / "guide" / "Guida-Cliente-LMC.pdf"), "-"], capture_output=True, text=True).stdout
for parola in ("Configuratore", "Installare l'app", "collaboratori", "QR 1"):
    check(f"Guida Cliente cita «{parola}»", parola in cli)

# ---- video: mini copione (2 scene, una con voce vera, una senza) in entrambi i formati
mini = {"titolo": "mini", "scene": [cop["tour"]["scene"][0], dict(cop["tour"]["scene"][1], id="zz-senza-voce")]}
for fmt, (vw, vh) in (("verticale", (1080, 1920)), ("orizzontale", (1920, 1080))):
    f = tmp / f"mini-{fmt}.mp4"
    p, dur, voci = kit_video.crea_video(mini, fmt, shots, f, out / "qr" / "QR1-app-clienti-semplice.png", "esempio.test")
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(f)], capture_output=True, text=True).stdout)
    v = [s for s in info["streams"] if s["codec_type"] == "video"]
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    check(f"video {fmt}: {vw}x{vh} H.264", v and (v[0]["width"], v[0]["height"]) == (vw, vh) and v[0]["codec_name"] == "h264", v)
    check(f"video {fmt}: traccia audio AAC", a and a[0]["codec_name"] == "aac")
    check(f"video {fmt}: durata sensata ({dur:.1f}s)", 10 < dur < 40)
    check(f"video {fmt}: una sola scena con voce", voci == 1, voci)
    chk = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-f", "null", "-"], capture_output=True, text=True)
    check(f"video {fmt}: si decodifica senza errori", chk.returncode == 0 and not chk.stderr.strip(), chk.stderr[-300:])

# ---- copioni coerenti: durata complessiva dentro 60-90 s, una voce per scena
for k in ("tour", "gestionale"):
    tot = 0
    for sc in cop[k]["scene"]:
        m = kit_video.AUDIO / f"{sc['id']}.mp3"
        check(f"voce presente per {sc['id']}", m.exists())
        if m.exists():
            tot += kit_video.durata(m) + 0.9
    check(f"video «{k}» tra 60 e 90 secondi ({tot:.0f}s)", 60 <= tot <= 90, tot)

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{ok} ok, {fail} falliti")
sys.exit(1 if fail else 0)
