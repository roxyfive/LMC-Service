"""Kit di consegna LMC: un solo comando che genera tutto in consegna/ (pronto da zippare).

    python -m backend.kit_consegna [--out consegna] [--url https://...] [--solo-pdf] [--senza-video] [--shots CARTELLA]

Contenuto:  guide/ (2 PDF)   qr/ (2 QR da stampare + versioni semplici)   video/ (2 video x 2 formati)   schermate/   LEGGIMI.txt
Gli screenshot sono fatti su un database TEMPORANEO con dati di prova (nessun dato reale, il database vero non viene toccato).
Le voci narranti sono gli mp3 in backend/kit_assets/audio/ (una per scena); se manca qualcosa e c'è ELEVENLABS_API_KEY nel .env viene generato.
"""
import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

from . import kit_pdf, kit_qr, kit_testi, kit_video

ROOT = Path(__file__).resolve().parent.parent
URL_DEFAULT = "https://lmcservice.duckdns.org"
LOGO = ROOT / "logo" / "fivetech.png"


def genera_voci(copioni, forza=False):
    """Genera con ElevenLabs gli mp3 mancanti (richiede ELEVENLABS_API_KEY). Ritorna quanti ne ha creati."""
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voce = copioni["voce"]
    n = 0
    for k in ("tour", "gestionale"):
        for sc in copioni[k]["scene"]:
            f = kit_video.AUDIO / f"{sc['id']}.mp3"
            if f.exists() and not forza:
                continue
            if not key:
                continue
            req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voce['voice_id']}",
                                         data=json.dumps({"text": sc["audio"], "model_id": voce["model"]}).encode(),
                                         headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(urllib.request.urlopen(req, timeout=120).read())
            n += 1
            time.sleep(1)
    return n


def scrivi_leggimi(out, url, risultati):
    admin = url.rstrip("/") + "/admin/login"
    righe = [f"KIT DI CONSEGNA - LMC SERVICE  (versione {kit_testi.VERSIONE}, {date.today().strftime('%d/%m/%Y')})", "", "Realizzato da FiveTech.", "",
             "CONTENUTO", "  guide/Guida-Admin-LMC.pdf      come usare il gestionale, passo per passo (per Pasquale)",
             "  guide/Guida-Cliente-LMC.pdf    come usare il sito e l'app (per Pasquale e collaboratori)",
             f"  qr/QR1-app-clienti.png         QR del sito/app clienti ({url})  - da stampare",
             f"  qr/QR2-accesso-admin.png       QR dell'accesso admin ({admin})  - SOLO uso interno",
             "  qr/*-semplice.png              solo il QR, da inserire in altri documenti",
             "  video/                         2 video (Tour sito, Gestire il gestionale), ciascuno verticale 9:16 e orizzontale 16:9",
             "  schermate/                     le schermate usate nelle guide (dati di prova)", "",
             "COSA RESTA DA FARE A MANO", "  1. Fatture > Dati fiscali: partita IVA, sede, IBAN, numerazione.", "  2. Tariffe: i prezzi del listino.",
             "  3. File .env sul server: PUBLIC_URL (link nelle email di recensione) e dati SMTP.",
             "  4. Utenti: creare gli account dei collaboratori e cambiare la password dell'admin.", "",
             "NOTA SUI QR", "  Il QR2 porta alla pagina di accesso: non basta per entrare (serve la password), ma stampalo solo per uso interno.", ""]
    for k, v in risultati.items():
        righe.append(f"  {k}: {v}")
    (out / "LEGGIMI.txt").write_text("\n".join(righe) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "consegna"))
    ap.add_argument("--url", default=os.getenv("PUBLIC_URL", "").strip() or URL_DEFAULT, help="indirizzo pubblico del sito (per i QR)")
    ap.add_argument("--solo-pdf", action="store_true", help="salta i video")
    ap.add_argument("--senza-video", action="store_true", help="come --solo-pdf")
    ap.add_argument("--shots", help="usa screenshot già fatti in questa cartella invece di rigenerarli")
    ap.add_argument("--rigenera-voci", action="store_true", help="rigenera tutte le voci narranti (serve ELEVENLABS_API_KEY)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    url = a.url.rstrip("/")
    admin_url = url + "/admin/login"
    ris = {}
    t0 = time.time()
    for sub in ("guide", "qr", "video", "schermate"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    print("1/5  QR code...")
    qr1, qr2 = out / "qr" / "QR1-app-clienti.png", out / "qr" / "QR2-accesso-admin.png"
    kit_qr.print_card(url, "APP CLIENTI", "Prenota e chiedi un preventivo da telefono", qr1, logo=LOGO)
    kit_qr.print_card(admin_url, "ACCESSO ADMIN", "Gestionale LMC - solo uso interno", qr2, logo=LOGO)
    s1, s2 = out / "qr" / "QR1-app-clienti-semplice.png", out / "qr" / "QR2-accesso-admin-semplice.png"
    kit_qr.plain(url, s1)
    kit_qr.plain(admin_url, s2)
    qrs = [("QR 1 - Sito e app clienti", url, s1), ("QR 2 - Accesso admin (uso interno)", admin_url, s2)]
    ris["QR"] = "4 file in qr/"

    print("2/5  Screenshot (dati di prova)...")
    if a.shots:
        shots = Path(a.shots)
    else:
        shots = out / "schermate"
        from . import kit_shots
        kit_shots.run_child(shots)
    if Path(shots).resolve() != (out / "schermate").resolve():       # screenshot riusati: copia nel kit solo quelli di sito e admin
        for f in Path(shots).glob("*.png"):
            if f.name.startswith(("admin-", "sito-")):
                shutil.copy(f, out / "schermate" / f.name)
    ris["Screenshot"] = f"{len(list((out / 'schermate').glob('*.png')))} in schermate/"

    print("3/5  Guide PDF...")
    d = date.today()
    pa = kit_pdf.build(out / "guide" / "Guida-Admin-LMC.pdf", "Guida Admin LMC", "Come usare il gestionale, passo per passo",
                       "Questa guida spiega ogni funzione del gestionale: a cosa serve, come si usa in pochi passi numerati, come si collegano tra loro "
                       "richieste, preventivi, fatture e acconti, quali permessi hanno ADMIN e COLLABORATORE e quali sono le specifiche tecniche.",
                       kit_testi.ADMIN, shots, qrs, extra=[("ruoli", "15. Ruoli e permessi"), ("specifiche", "16. Specifiche tecniche")], data=d)
    pc = kit_pdf.build(out / "guide" / "Guida-Cliente-LMC.pdf", "Guida Cliente LMC", "Il sito e l'app di La Music Company Service",
                       "Per Pasquale e per i collaboratori: come funziona il sito che vedono i clienti (servizi, galleria, configuratore, prenotazione), "
                       "come si installa come app e cosa possono fare i collaboratori nel gestionale.", kit_testi.CLIENTE, shots, qrs, data=d)
    ris["PDF"] = ", ".join(f"{p.name} ({p.stat().st_size // 1024} KB)" for p in (pa, pc))

    if a.solo_pdf or a.senza_video:
        ris["Video"] = "saltati"
    else:
        print("4/5  Voci narranti...")
        cop = kit_video.copioni()
        nuove = genera_voci(cop, forza=a.rigenera_voci)
        mancanti = [s["id"] for k in ("tour", "gestionale") for s in cop[k]["scene"] if not (kit_video.AUDIO / f"{s['id']}.mp3").exists()]
        ris["Voce narrante"] = f"{nuove} generate ora, {len(mancanti)} scene senza voce" + (f" ({', '.join(mancanti)})" if mancanti else "")
        print("5/5  Video (qualche minuto)...")
        vids = []
        for chiave, nome, qrv, uv in (("tour", "Tour-sito-LMC", s1, url), ("gestionale", "Gestire-il-gestionale", s2, admin_url)):
            for fmt, suf in (("verticale", "9x16"), ("orizzontale", "16x9")):
                f, dur, voci = kit_video.crea_video(cop[chiave], fmt, shots, out / "video" / f"{nome}-{suf}.mp4", qrv, uv.replace("https://", ""))
                vids.append(f"{f.name} ({dur:.0f} s, {f.stat().st_size // 1024 // 1024} MB, {voci} scene con voce)")
                print("   ", vids[-1])
        ris["Video"] = "; ".join(vids)

    scrivi_leggimi(out, url, ris)
    print(f"\nFatto in {time.time() - t0:.0f} s -> {out}")
    for k, v in ris.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
