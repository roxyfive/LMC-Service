"""I due PDF per l'agenzia (docs/Libretto-LMC.pdf e docs/Guida-Agenzia-LMC.pdf): python -m tests.test_pdf_consegna
Presenti, completi, con indice cliccabile, logo FiveTech nelle pagine interne e contenuti chiave."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


def testo(pdf, a=None, b=None):
    cmd = ["pdftotext", "-layout"] + (["-f", str(a), "-l", str(b)] if a else []) + [str(pdf), "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

lib, ag = ROOT / "docs" / "Libretto-LMC.pdf", ROOT / "docs" / "Guida-Agenzia-LMC.pdf"
check("i due PDF esistono (e solo questi due per l'agenzia)", lib.exists() and ag.exists() and not (ROOT / "docs" / "Guida-SMTP-LMC.pdf").exists())
t = testo(lib)
for parola in ("Dashboard", "Agenda", "Fatture", "Acconti", "Recensioni", "Galleria", "Utenti e permessi", "Registro delle attività", "Backup", "COLLABORATORE", "Scheda rapida del collaboratore",
               "Architettura", "Sicurezza", "Messa online e aggiornamento", "Cosa resta da completare", "Glossario", "La nostra storia", "Accesso e sicurezza"):
    check(f"Libretto cita «{parola}»", parola in t)
check("Libretto: nessun segnaposto o testo di prova rimasto", "DA COMPLETARE" not in t and "lorem" not in t.lower())
ta = testo(ag)
for parola in ("SMTP", "Dominio .it", "Pasquale Toppi", "SMTP_PASSWORD", "collega-dominio.sh", "SPF", "Checklist finale"):
    check(f"Guida agenzia cita «{parola}»", parola in ta)
check("Guida agenzia: nessuna password scritta", "SMTP_PASSWORD=<" in ta and "password per le app, senza spazi>" in ta)
if PdfReader:
    for nome, pdf, minp, minlink in (("Libretto", lib, 50, 45), ("Guida agenzia", ag, 7, 0)):
        rd = PdfReader(str(pdf))
        n = len(rd.pages)
        check(f"{nome}: pagine ({n})", n >= minp)
        check(f"{nome}: logo FiveTech nelle pagine interne", sum(1 for p in rd.pages[1:] if len(p.images) >= 1) >= n * 0.6)
        if minlink:
            link = sum(1 for p in rd.pages[1:4] for a in (p.get("/Annots") or []) if a.get_object().get("/Subtype") == "/Link")
            check(f"{nome}: indice cliccabile ({link} link)", link >= minlink)
            check(f"{nome}: segnalibri", len(rd.outline) >= 6)
        check(f"{nome}: titolo e autore nel file", (rd.metadata.title or "") != "" and (rd.metadata.author or "") == "FiveTech")
    check("Libretto: pesa meno di 20 MB (si può mandare via email)", lib.stat().st_size < 20 * 1024 * 1024)
else:
    print("SKIP controlli di struttura (pypdf non installato)")
print(f"\n{ok} ok, {fail} falliti")
sys.exit(1 if fail else 0)
