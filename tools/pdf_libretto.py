"""Genera docs/Libretto-LMC.pdf: libretto illustrativo completo (clienti, admin, collaboratori, specifiche).
Uso:  python -m tools.libretto_shots CARTELLA_SHOT   (una volta)   poi   python -m tools.pdf_libretto CARTELLA_SHOT [uscita.pdf]"""
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

from tools.libretto_lib import *  # noqa: F401,F403
from tools import libretto_lib as L

SHOTS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/claude-0/libshots2")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "Libretto-LMC.pdf"
QR1, QR2 = SHOTS / "qr1.png", SHOTS / "qr2.png"


# ============================================================ diagrammi
def D(h):
    return Drawing(CW, h)


def testo(d, x, y, t, col=ANTRA, fs=8, bold=False, anchor="middle"):
    d.add(String(x, y, t, fontName="Inter-Bold" if bold else "Inter", fontSize=fs, fillColor=col, textAnchor=anchor))


def d_mappa():
    d = D(112 * mm)
    # pannello server
    d.add(Rect(56 * mm, 8 * mm, 66 * mm, 98 * mm, rx=9, ry=9, fillColor=colors.HexColor("#ececf1"), strokeColor=BORDO))
    testo(d, 89 * mm, 99 * mm, "SERVER LMC · VPS IONOS · HTTPS", ANTRA, 8.5, True)
    L._box(d, 60 * mm, 66 * mm, 58 * mm, 26 * mm, "Sito pubblico e App", ["vetrina, video, galleria,", "prenotazioni, preventivi"], TEAL)
    L._box(d, 60 * mm, 36 * mm, 58 * mm, 26 * mm, "Gestionale", ["agenda, fatture, acconti,", "recensioni, utenti e ruoli"], ROSSO)
    L._box(d, 60 * mm, 11 * mm, 58 * mm, 21 * mm, "Dati e file", ["database SQLite, foto, impostazioni"], ANTRA)
    # lato sinistro
    L._box(d, 0, 66 * mm, 44 * mm, 26 * mm, "Clienti", ["telefono, computer,", "app installata"], TEAL)
    L._box(d, 0, 36 * mm, 44 * mm, 26 * mm, "Staff", ["Admin (titolare)", "e collaboratori"], ROSSO)
    L._arrow(d, 44.8 * mm, 79 * mm, 59.2 * mm, 79 * mm, TEAL)
    L._arrow(d, 44.8 * mm, 49 * mm, 59.2 * mm, 49 * mm, ROSSO)
    L._arrow(d, 89 * mm, 66 * mm, 89 * mm, 62.8 * mm, GRIGIO)
    L._arrow(d, 89 * mm, 36 * mm, 89 * mm, 32.8 * mm, GRIGIO)
    # servizi esterni
    ext = [("Email (SMTP)", ["conferme e avvisi", "da attivare"], AMBRA, 80), ("WhatsApp (Twilio)", ["avvisi al team", "opzionale"], colors.HexColor("#3a3a44"), 59),
           ("Assistente vocale (Vapi)", ["voce naturale", "opzionale"], colors.HexColor("#3a3a44"), 38), ("Backup su cloud", ["copia cifrata", "ogni notte"], VERDE, 11)]
    for t, r_, col, y in ext:
        L._box(d, 134 * mm, y * mm, 40 * mm, 21 * mm, t, r_, col, fs=8.6)
    L._arrow(d, 118.8 * mm, 85 * mm, 133.2 * mm, 90 * mm, AMBRA, dash=True)
    L._arrow(d, 118.8 * mm, 50 * mm, 133.2 * mm, 66 * mm, GRIGIO, dash=True)
    L._arrow(d, 118.8 * mm, 45 * mm, 133.2 * mm, 48 * mm, GRIGIO, dash=True)
    L._arrow(d, 118.8 * mm, 20 * mm, 133.2 * mm, 21 * mm, VERDE)
    testo(d, 0, 2 * mm, "Frecce piene: funziona oggi · frecce tratteggiate: da attivare o facoltativo", GRIGIO, 7.4, anchor="start")
    return d


def d_ruoli():
    d = D(70 * mm)
    d.add(Rect(0, 0, 112 * mm, 70 * mm, rx=10, ry=10, fillColor=colors.HexColor("#fbeaea"), strokeColor=ROSSO, strokeWidth=1.4))
    testo(d, 56 * mm, 62 * mm, "ADMIN (titolare): tutto", ROSSO, 10, True)
    testo(d, 56 * mm, 56 * mm, "fatture, acconti, tariffe, statistiche, utenti, impostazioni, backup, pubblicazione", GRIGIO, 7.2)
    d.add(Rect(8 * mm, 6 * mm, 96 * mm, 44 * mm, rx=8, ry=8, fillColor=colors.HexColor("#fff3dc"), strokeColor=AMBRA, strokeWidth=1.4))
    testo(d, 56 * mm, 42 * mm, "COLLABORATORE: il lavoro di ogni giorno", AMBRA, 9.6, True)
    for i, t in enumerate(["Dashboard e agenda · Richieste", "Galleria: carica foto (restano nascoste)", "Materiale, eventi, assistente e chat"]):
        testo(d, 56 * mm, (35 - i * 5.5) * mm, t, ANTRA, 8)
    d.add(Rect(122 * mm, 6 * mm, 52 * mm, 58 * mm, rx=10, ry=10, fillColor=colors.HexColor("#e6f5f2"), strokeColor=TEAL, strokeWidth=1.4))
    testo(d, 148 * mm, 54 * mm, "CLIENTE", TEAL, 10, True)
    for i, t in enumerate(["Sito e app pubblici", "Prenota, chiede preventivi", "Lascia recensioni", "Non entra nel gestionale"]):
        testo(d, 148 * mm, (45 - i * 6) * mm, t, ANTRA, 7.8)
    return d


def d_pratica():
    d = D(64 * mm)
    voci = [("Richiesta", ["dal sito o", "dal telefono"], TEAL), ("Preventivo", ["prezzi dal", "listino"], BLU), ("Conferma", ["entra in", "agenda"], AMBRA),
            ("Fattura", ["numero", "progressivo"], ROSSO), ("Acconti", ["anche a", "rate"], colors.HexColor("#8a2be2")), ("Saldato", ["pratica", "chiusa"], VERDE)]
    riga(d, 32 * mm, voci, h=24 * mm, gap=6.5 * mm, fs=9)
    dove = ["Richieste", "Preventivi", "Agenda", "Fatture", "Acconti", "Statistiche"]
    n = 6
    w = (CW - 6.5 * mm * 5) / n
    for i, t in enumerate(dove):
        x = i * (w + 6.5 * mm)
        testo(d, x + w / 2, 27 * mm, "dove: " + t, GRIGIO, 7.4, True)
    testo(d, 0, 18 * mm, "Dopo la conferma di un appuntamento il gestionale propone da solo di creare la fattura e di registrare l'acconto.", ANTRA, 8, anchor="start")
    testo(d, 0, 11 * mm, "Se la scadenza passa senza saldo la fattura diventa «scaduta» (in rosso). Dopo l'evento parte la richiesta di recensione.", ANTRA, 8, anchor="start")
    return d


def d_stati_fattura():
    d = D(52 * mm)
    L._box(d, 0, 26 * mm, 36 * mm, 20 * mm, "Bozza", ["senza numero"], colors.HexColor("#3a3a44"))
    L._box(d, 46 * mm, 26 * mm, 36 * mm, 20 * mm, "Emessa", ["numero F2026-001"], BLU)
    L._box(d, 92 * mm, 26 * mm, 36 * mm, 20 * mm, "Parziale", ["incassato in parte"], AMBRA)
    L._box(d, 138 * mm, 26 * mm, 36 * mm, 20 * mm, "Pagata", ["incassato tutto"], VERDE)
    for x in (36, 82, 128):
        L._arrow(d, (x + 0.8) * mm, 36 * mm, (x + 9.2) * mm, 36 * mm)
    L._box(d, 46 * mm, 0, 36 * mm, 17 * mm, "Scaduta", ["scadenza superata"], ROSSO)
    L._box(d, 92 * mm, 0, 36 * mm, 17 * mm, "Annullata", ["il numero resta"], colors.HexColor("#3a3a44"))
    L._arrow(d, 64 * mm, 26 * mm, 64 * mm, 17.8 * mm, ROSSO, dash=True)
    L._arrow(d, 74 * mm, 26 * mm, 100 * mm, 17.8 * mm, GRIGIO, dash=True)
    testo(d, 136 * mm, 8 * mm, "Il numero si assegna solo all'emissione:", GRIGIO, 7.6, anchor="start")
    testo(d, 136 * mm, 3.5 * mm, "niente buchi nella numerazione.", GRIGIO, 7.6, anchor="start")
    return d


def d_recensione():
    d = D(34 * mm)
    riga(d, 6 * mm, [("Evento finito", ["il giorno dopo"], colors.HexColor("#3a3a44")), ("Email al cliente", ["link personale"], BLU), ("Il cliente", ["stelle e testo"], TEAL),
                     ("In attesa", ["non è pubblica"], AMBRA), ("Admin approva", ["o rifiuta"], ROSSO), ("Sul sito", ["nome, stelle,", "evento"], VERDE)], h=22 * mm, gap=5.5 * mm, fs=8.4)
    return d


def d_galleria():
    d = D(32 * mm)
    riga(d, 5 * mm, [("Carichi la foto", ["Admin o", "collaboratore"], BLU), ("Didascalia", ["obbligatoria", "tipo e data"], AMBRA), ("Nascosta", ["bozza: nessuno", "la vede"], colors.HexColor("#3a3a44")),
                     ("Controllo", ["anteprima"], TEAL), ("Pubblica", ["solo Admin"], ROSSO)], h=22 * mm, gap=7 * mm, fs=8.8)
    return d


def d_giornata():
    d = D(52 * mm)
    for i, (t, righe, col) in enumerate([("MATTINA", ["Apri la Dashboard", "Conferma o rifiuta le richieste", "Guarda l'agenda di oggi"], TEAL), ("DURANTE", ["Controlla materiale e orari", "Scrivi le note del giorno", "Carica le foto (bozze)"], AMBRA),
                                         ("SERA", ["Rispondi alle richieste ferme", "Controlla gli eventi di domani", "Esci dal gestionale"], BLU)]):
        x = i * (CW / 3 + 0.5 * mm)
        w = CW / 3 - 3 * mm
        d.add(Rect(x, 0, w, 50 * mm, rx=8, ry=8, fillColor=colors.HexColor("#f4f4f7"), strokeColor=col, strokeWidth=1.4))
        d.add(Rect(x, 40 * mm, w, 10 * mm, rx=8, ry=8, fillColor=col, strokeColor=None))
        testo(d, x + w / 2, 43.4 * mm, t, colors.white, 9.2, True)
        for k, r_ in enumerate(righe):
            testo(d, x + w / 2, (31 - k * 9) * mm, r_, ANTRA, 7.8)
    return d


def d_arch():
    d = D(118 * mm)
    L._box(d, 0, 96 * mm, 38 * mm, 18 * mm, "Browser", ["sito, app, admin"], TEAL)
    L._box(d, 48 * mm, 96 * mm, 38 * mm, 18 * mm, "nginx", ["HTTPS, gzip, redirect"], ANTRA)
    L._box(d, 96 * mm, 96 * mm, 38 * mm, 18 * mm, "gunicorn", ["2 worker × 4 thread"], ANTRA)
    L._arrow(d, 38.8 * mm, 105 * mm, 47.2 * mm, 105 * mm)
    L._arrow(d, 86.8 * mm, 105 * mm, 95.2 * mm, 105 * mm)
    d.add(Rect(0, 38 * mm, 174 * mm, 52 * mm, rx=9, ry=9, fillColor=colors.HexColor("#ececf1"), strokeColor=BORDO))
    testo(d, 87 * mm, 83 * mm, "APPLICAZIONE FLASK (Python)", ANTRA, 8.6, True)
    mod = [("Pubblico", ["pagine, API chat,", "prenotazioni"], TEAL), ("Admin e gestionale", ["agenda, fatture,", "acconti, tariffe"], ROSSO), ("Ruoli e sicurezza", ["permessi, CSRF,", "registro attività"], BLU),
           ("Recensioni e email", ["link personali,", "SMTP"], AMBRA)]
    w = (170 * mm - 3 * 4 * mm) / 4
    for i, (t, r_, col) in enumerate(mod):
        L._box(d, 2 * mm + i * (w + 4 * mm), 42 * mm, w, 34 * mm, t, r_, col, fs=8.6)
    L._arrow(d, 115 * mm, 96 * mm, 115 * mm, 90.8 * mm)
    L._box(d, 0, 4 * mm, 54 * mm, 24 * mm, "SQLite (modalità WAL)", ["un solo file di database"], ANTRA)
    L._box(d, 60 * mm, 4 * mm, 54 * mm, 24 * mm, "File su disco", ["foto, video, impostazioni"], ANTRA)
    L._box(d, 120 * mm, 4 * mm, 54 * mm, 24 * mm, "Attività di fondo", ["promemoria, report, pulizia"], colors.HexColor("#3a3a44"))
    for x in (27, 87, 147):
        L._arrow(d, x * mm, 38 * mm, x * mm, 28.8 * mm, GRIGIO)
    return d


def d_sicurezza():
    d = D(44 * mm)
    riga(d, 6 * mm, [("1. Rete", ["HTTPS obbligatorio", "HSTS, redirect"], BLU), ("2. Accesso", ["password ≥ 10", "blocco tentativi"], AMBRA), ("3. Permessi", ["ruoli controllati", "dal server"], ROSSO),
                     ("4. Dati", ["backup cifrati", "anonimizzazione"], VERDE)], h=30 * mm, gap=7 * mm, fs=9.6)
    testo(d, 0, 1 * mm, "Quattro livelli: se uno viene superato gli altri continuano a proteggere i dati.", GRIGIO, 7.6, anchor="start")
    return d


def d_backup():
    d = D(40 * mm)
    riga(d, 8 * mm, [("03:20", ["parte il", "backup"], colors.HexColor("#3a3a44")), ("Raccolta", ["database, foto,", "impostazioni"], BLU), ("Cifratura", ["con password", "del server"], AMBRA),
                     ("Copie", ["sul server e su", "un cloud esterno"], VERDE), ("Verifica", ["la copia cloud", "viene riletta"], TEAL), ("Esito", ["visibile in", "Admin › Backup"], ROSSO)], h=26 * mm, gap=5.5 * mm, fs=8.6)
    return d


def d_deploy():
    d = D(44 * mm)
    riga(d, 12 * mm, [("1. Sviluppo", ["codice nel repo", "GitHub"], colors.HexColor("#3a3a44")), ("2. aggiorna.sh", ["backup, pull,", "dipendenze"], BLU), ("3. Riavvio", ["servizio lmc"], AMBRA),
                      ("4. Controllo", ["/health e", "verifica-online"], VERDE)], h=26 * mm, gap=8 * mm, fs=9.2)
    testo(d, 0, 4 * mm, "Se un passaggio fallisce lo script si ferma e il sito resta com'era.", GRIGIO, 7.6, anchor="start")
    return d


def d_email():
    d = D(44 * mm)
    riga(d, 14 * mm, [("1. Cliente", ["compila il modulo"], TEAL), ("2. Sito LMC", ["prepara l'email"], ANTRA), ("3. Server SMTP", ["l'«ufficio postale»"], ROSSO), ("4. Destinatari", ["cliente e Pasquale"], VERDE)], h=24 * mm, gap=8 * mm, fs=9.2)
    testo(d, 0, 6 * mm, "Oggi il passaggio 3 non è attivo: le email restano in un file sul server. Vedi la «Guida per l'agenzia».", AMBRA, 8, True, anchor="start")
    return d


def sez(titolo_, ruoli, scopo=None, extra=(), key=None, level=1):
    out = titolo(titolo_, ruoli, key, level)
    if scopo:
        out.append(Paragraph(scopo, lead))
        out.append(Spacer(1, 2.5 * mm))
    out += list(extra)
    return out


def H2(t):
    return Paragraph(t, h2)


# ============================================================ copertine e struttura
def PT(n, nome, sotto, voci, col):
    return [NextPageTemplate("div"), PageBreak(), Divider(n, nome, sotto, voci, col), NextPageTemplate(f"p{n}"), PageBreak()]


def copertina(c, doc):
    c.saveState()
    c.setFillColor(NERO)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    ir = ImageReader(str(LOGO_LMC))
    ih = W * ir.getSize()[1] / ir.getSize()[0]
    c.drawImage(ir, 0, H - ih, width=W, height=ih)
    c.setFillColor(ROSSO)
    c.rect(0, H - ih - 2 * mm, W, 2 * mm, stroke=0, fill=1)
    y = H - ih - 30 * mm
    c.setFont("Inter-Bold", 10.5)
    c.setFillColor(ROSSO2)
    c.drawString(M, y, "LIBRETTO ILLUSTRATIVO · VERSIONE " + VERSIONE)
    c.setFillColor(colors.white)
    c.setFont("Mont", 42)
    c.drawString(M, y - 19 * mm, "Sito, App e")
    c.drawString(M, y - 36 * mm, "Gestionale")
    c.setFont("Inter", 13)
    c.setFillColor(colors.HexColor("#c8c8d2"))
    c.drawString(M, y - 49 * mm, "La guida completa di La Music Company Service:")
    c.drawString(M, y - 56 * mm, "come funziona, come si usa, come è costruito.")
    x = M
    for r in ("CLIENTI", "ADMIN", "COLLABORATORI", "SPECIFICHE TECNICHE"):
        col = {"CLIENTI": TEAL, "ADMIN": ROSSO, "COLLABORATORI": AMBRA}.get(r, BLU)
        w = pdfmetrics.stringWidth(r, "Inter-Bold", 8) + 7 * mm
        c.setFillColor(col)
        c.roundRect(x, y - 74 * mm, w, 6.5 * mm, 3.2 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Inter-Bold", 8)
        c.drawCentredString(x + w / 2, y - 72 * mm, r)
        x += w + 3 * mm
    # firma
    c.setFillColor(colors.white)
    c.roundRect(M, 12 * mm, 62 * mm, 22 * mm, 4 * mm, stroke=0, fill=1)
    logo_ft(c, M + 5 * mm, 14.5 * mm, 17 * mm)
    c.setFont("Inter", 8.5)
    c.setFillColor(colors.HexColor("#9a9aa8"))
    c.drawRightString(W - M, 28 * mm, "Preparato da FiveTech")
    c.drawRightString(W - M, 22.5 * mm, date.today().strftime("%d/%m/%Y"))
    c.drawRightString(W - M, 17 * mm, "Documento riservato · dati di esempio nelle schermate")
    c.restoreState()


def retro(c, doc):
    c.saveState()
    c.setFillColor(NERO)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    ir = ImageReader(str(LOGO_LMC))
    ih = W * ir.getSize()[1] / ir.getSize()[0]
    c.saveState()
    c.setFillAlpha(0.3)
    c.drawImage(ir, 0, 0, width=W, height=ih)
    c.restoreState()
    c.setFillColor(ROSSO)
    c.rect(0, H - 8 * mm, W, 8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Mont", 30)
    c.drawString(M, H - 50 * mm, "Tutto a portata")
    c.drawString(M, H - 63 * mm, "di telefono.")
    c.setFont("Inter", 12)
    c.setFillColor(colors.HexColor("#c8c8d2"))
    c.drawString(M, H - 76 * mm, "Inquadra i codici con la fotocamera.")
    for i, (qr, tit, sub) in enumerate(((QR1, "APP CLIENTI", "Il sito di LMC: prenota e chiedi un preventivo"), (QR2, "ACCESSO ADMIN", "Gestionale: solo per titolare e collaboratori"))):
        x = M + i * 88 * mm
        c.setFillColor(colors.white)
        c.roundRect(x, H - 152 * mm, 80 * mm, 64 * mm, 5 * mm, stroke=0, fill=1)
        if qr.exists():
            c.drawImage(ImageReader(str(qr)), x + 15 * mm, H - 148 * mm, width=50 * mm, height=50 * mm)
        c.setFillColor(ROSSO2)
        c.setFont("Inter-Bold", 11)
        c.drawString(x, H - 160 * mm, tit)
        c.setFont("Inter", 8.5)
        c.setFillColor(colors.HexColor("#c8c8d2"))
        c.drawString(x, H - 166 * mm, sub)
    c.setFillColor(colors.white)
    c.roundRect(M, 14 * mm, 62 * mm, 22 * mm, 4 * mm, stroke=0, fill=1)
    logo_ft(c, M + 5 * mm, 16.5 * mm, 17 * mm)
    c.setFont("Inter", 9)
    c.setFillColor(colors.HexColor("#c8c8d2"))
    c.drawRightString(W - M, 30 * mm, "La Music Company Service · Napoli")
    c.drawRightString(W - M, 24.5 * mm, "Audio · Video · Luci")
    c.restoreState()


class Fine(Flowable):
    """Pagina finale a pieno foglio (disegnata da retro())."""

    def wrap(self, aw, ah):
        return aw, ah - 1

    def draw(self):
        self.canv.saveState()
        self.canv.translate(-M, -20 * mm)
        retro(self.canv, None)
        self.canv.restoreState()


class DocLib(BaseDocTemplate):
    def afterFlowable(self, fl):
        t = getattr(fl, "_toc", None)
        if t:
            lvl, txt, key = t
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(txt, key, lvl, 0)
            self.notify("TOCEntry", (lvl, txt, self.page, key))


def indice():
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t0", fontName="Inter-Bold", fontSize=11, leading=19, textColor=ANTRA, spaceBefore=6),
                       ParagraphStyle("t1", fontName="Inter", fontSize=9.2, leading=13.6, leftIndent=11, textColor=GRIGIO)]
    toc.dotsMinLevel = 1
    return toc


def pagina_come_leggere():
    out = titolo("Come leggere questo libretto", None, "come_leggere", 0)
    out += [Paragraph("Questo libretto accompagna il sito e il gestionale di La Music Company Service dal primo sguardo fino ai dettagli tecnici. "
                      "Ogni capitolo è pensato per una persona diversa: puoi leggere solo la parte che ti riguarda.", lead), Spacer(1, 4 * mm)]
    righe = [["Etichetta", "Per chi è", "Dove"],
             [Chips(["CLIENTE"]), "Chi visita il sito o usa l'app: prenota, chiede un preventivo, guarda i lavori.", "Parte 2"],
             [Chips(["ADMIN"]), "Il titolare: gestisce tutto, comprese fatture, incassi, utenti e impostazioni.", "Parti 1, 3 e 6"],
             [Chips(["COLLABORATORE"]), "Chi lavora con il titolare: agenda, richieste, foto, materiale. Non vede fatture e incassi.", "Parte 4"],
             [Chips(["TECNICO"]), "Chi gestisce il server, l'agenzia o chi deve capire come è costruito.", "Parte 5"]]
    out.append(tabella(righe, [40 * mm, 104 * mm, 30 * mm]))
    out += [Spacer(1, 5 * mm), H2("Come sono fatte le pagine"),
            tabella([["Elemento", "Cosa significa"],
                     ["Numeri rossi sulle schermate", "Corrispondono alla legenda accanto: ti dicono cosa guardare e dove cliccare."],
                     ["Riquadro «Consiglio»", "Un'abitudine utile, per lavorare meglio."],
                     ["Riquadro «Attenzione»", "Qualcosa che può creare problemi se si sbaglia."],
                     ["Riquadro «Sicurezza»", "Una regola per proteggere dati e accessi. Va sempre rispettata."],
                     ["Riquadro «Da sapere»", "Un'informazione di contesto."],
                     ["Indice cliccabile", "Nelle pagine 3-4 tocca una voce per saltare al capitolo. I segnalibri del lettore PDF funzionano allo stesso modo."]],
                    [58 * mm, 116 * mm]),
            Spacer(1, 4 * mm),
            nota("Le schermate del gestionale mostrano <b>dati di esempio</b> (nomi, importi e richieste inventati): nessun dato reale di clienti compare in questo libretto.", "info"),
            Spacer(1, 3 * mm),
            nota("Alcune funzioni sono pronte ma <b>da attivare</b>: l'invio delle email (SMTP), il dominio .it e i dati fiscali. Sono elencate nella Parte 6.", "attenzione")]
    return out


story = [Spacer(1, 1), NextPageTemplate("p00"), PageBreak()]
story += titolo("Indice", None, "indice", 0)
story += [Paragraph("Tocca un titolo per andare al capitolo.", small), Spacer(1, 3 * mm), indice(), PageBreak()]
story += pagina_come_leggere()

# ============================================================ PARTE 1
story += PT(1, "Il progetto\nin breve", "Che cosa è stato costruito, chi lo usa e come\nlavora una pratica dal primo contatto all'incasso.",
            ["Che cosa abbiamo costruito", "Chi usa cosa: i ruoli", "Il percorso di una pratica"], ROSSO)
story += sez("Che cosa abbiamo costruito", ["ADMIN", "CLIENTE"], "Un sito vetrina moderno, un'app installabile e un gestionale completo, ospitati su un server proprio con backup cifrati ogni notte.", [
    d_mappa(), Spacer(1, 3 * mm),
    tabella([["Il pezzo", "Cosa fa", "Chi lo usa"],
             ["Sito pubblico e app (PWA)", "Presenta La Music Company Service: video della storia, galleria, servizi, configuratore, prenotazioni e preventivi, assistente AI, emergenza 24 ore. Si installa sul telefono come un'app.", "Clienti"],
             ["Gestionale (area Admin)", "Dashboard, agenda, richieste, preventivi, fatture con PDF, acconti, recensioni, galleria eventi, tariffe, statistiche, utenti con ruoli, registro delle attività, backup.", "Titolare e collaboratori"],
             ["Server e sicurezza", "VPS IONOS con HTTPS, accessi protetti, permessi per ruolo, conservazione dei dati a norma, backup cifrato su uno spazio cloud.", "Tecnico / agenzia"],
             ["Controlli automatici", "Oltre 640 verifiche automatiche su sito, permessi, fatture, accessibilità, privacy, grafica e backup: prima di ogni aggiornamento.", "Tecnico"]],
            [40 * mm, 100 * mm, 34 * mm])])
story += [PageBreak()]
story += sez("Chi usa cosa: i ruoli", ["ADMIN", "COLLABORATORE", "CLIENTE"], "Ogni persona vede solo ciò che le serve. Il controllo dei permessi lo fa il server, non solo il menu: una pagina vietata non si apre nemmeno scrivendo l'indirizzo a mano.", [
    d_ruoli(), Spacer(1, 3 * mm),
    tabella([["Funzione", "Admin", "Collaboratore", "Cliente"],
             ["Sito e app pubblici", "Sì", "Sì", "Sì"], ["Dashboard, agenda, richieste", "Sì", "Sì (senza incassi)", "No"], ["Preventivi", "Sì", "No", "No"],
             ["Fatture, acconti e incassi", "Sì", "No", "No"], ["Galleria: caricare foto", "Sì", "Sì (restano nascoste)", "No"], ["Galleria: pubblicare o eliminare", "Sì", "No", "No"],
             ["Materiale, eventi, assistente e chat", "Sì", "Sì", "No"], ["Recensioni, clienti, team", "Sì", "No", "No"], ["Tariffe, statistiche, impostazioni, backup", "Sì", "No", "No"],
             ["Utenti, permessi, registro attività", "Sì", "No", "No"]], [70 * mm, 24 * mm, 46 * mm, 34 * mm]), Spacer(1, 3 * mm),
    nota("L'ultimo Admin non si può disattivare né declassare: così non resti mai chiuso fuori dal gestionale.", "info"), Spacer(1, 2 * mm),
    nota("Ogni azione sensibile (fatture, incassi, utenti, impostazioni, foto) viene registrata: <b>chi</b>, <b>cosa</b>, <b>quando</b>. Solo l'Admin può leggere il registro.", "sicurezza")])
story += [PageBreak()]
story += sez("Il percorso di una pratica", ["ADMIN", "COLLABORATORE"], "Dalla richiesta del cliente all'incasso finale: sei passaggi, sempre nello stesso ordine.", [
    d_pratica(), Spacer(1, 3 * mm),
    tabella([["Passo", "Dove si fa", "Cosa succede", "Chi"],
             ["1. Richiesta", "Richieste", "Il cliente compila il modulo del sito: la richiesta compare nella Dashboard e in Richieste.", "Tutti"],
             ["2. Preventivo", "Preventivi", "Si prepara il preventivo con i prezzi del listino (Tariffe) e si scarica il PDF.", "Admin"],
             ["3. Conferma", "Agenda", "Si conferma l'appuntamento: la data entra in agenda e il cliente riceve la conferma (con le email attive).", "Tutti"],
             ["4. Fattura", "Fatture", "Il preventivo accettato diventa fattura. Il numero si assegna solo quando la emetti.", "Admin"],
             ["5. Acconti", "Acconti", "Si registrano i pagamenti, anche a rate. Il sistema calcola il residuo.", "Admin"],
             ["6. Saldato", "Fatture, Statistiche", "Quando il versato arriva al totale la fattura è «pagata» e finisce negli incassi.", "Admin"]],
            [24 * mm, 30 * mm, 98 * mm, 22 * mm]), Spacer(1, 3 * mm),
    nota("Dopo l'evento il gestionale può chiedere una <b>recensione</b> al cliente: la pubblichi solo se la approvi (capitolo Recensioni).", "consiglio"),
    H2("Gli stati di una fattura"), d_stati_fattura()])

# ============================================================ PARTE 2 · CLIENTI
def cl(titolo_, scopo, stem, did, passi_, note_=None, extra=()):
    o = sez(titolo_, ["CLIENTE"], scopo)
    o.append(coppia(SHOTS, stem, did))
    o.append(Spacer(1, 3 * mm))
    if passi_:
        o += [H2("Come si usa"), passi(passi_, TEAL)]
    for n in (note_ or []):
        o += [Spacer(1, 2.5 * mm), nota(n[1], n[0])]
    o += list(extra)
    return o


story += PT(2, "Per i clienti:\nil sito e l'app", "Come funziona il sito di La Music Company Service\nvisto da chi lo visita, dal telefono o dal computer.",
            ["Primo sguardo: intro e home", "La nostra storia (video)", "Servizi, galleria e show demo", "Configuratore e preventivo", "Prenotare un appuntamento",
             "Contatti, emergenza e assistente AI", "Recensioni e installazione dell'app", "Privacy, cookie e accessibilità"], TEAL)
story += cl("Primo sguardo: intro e home", "Il sito si apre con un breve filmato di benvenuto e poi mostra subito cosa fa La Music Company Service e come contattarla.", "sito-home",
            "La home: titolo, due pulsanti principali («Richiedi un preventivo», «Prenota un appuntamento») e il link «Guarda la nostra storia».",
            ["All'apertura parte l'<b>intro</b>: 6 immagini con musica e voce (si può attivare l'audio con un tocco). <b>«Entra nel sito»</b> la salta in qualsiasi momento.",
             "La home mostra il claim, i servizi principali e il numero di telefono sempre a portata di tocco.",
             "I pulsanti in alto portano al modulo di preventivo o alla prenotazione di un appuntamento.",
             "Il menu (su telefono: icona in alto a destra) porta a Chi siamo, Skill, Eventi, Come lavoriamo, Prenota e Contatti."],
            [("info", "L'intro si rivede quando vuoi dal link «Rivedi l'intro» in fondo al sito.")])
story += [PageBreak()]
story += cl("La nostra storia (video)", "Un video di circa tre minuti racconta come è nata La Music Company: appare subito sotto la striscia 24/7, in una sezione grande e centrata.", "sito-storia",
            "La sezione «Ogni grande evento ha una storia. Ecco la nostra.» con il player in tema scuro e il tasto play centrale.",
            ["Premi il tasto <b>play</b> al centro del video: il filmato si scarica solo in quel momento, per non rallentare il sito.",
             "Con i controlli del lettore puoi mettere in pausa, spostarti nel filmato, regolare il volume e passare a <b>schermo intero</b>.",
             "I <b>sottotitoli in italiano</b> si attivano dall'icona CC del lettore.",
             "Dal pulsante «Guarda la nostra storia» della home il sito scorre direttamente a questa sezione."],
            [("consiglio", "Su telefono, ruota lo schermo in orizzontale prima di passare a schermo intero: il video è a 16:9.")])
story += [PageBreak()]
story += cl("Servizi, galleria e show demo", "Le sezioni «Le nostre skill», «Eventi realizzati» e «Show demo» mostrano cosa sa fare La Music Company con foto e video veri.", "sito-skill",
            "Le quattro card dei servizi: Ledwall, Audio, Allestimenti, Eventi. Ognuna porta al preventivo.",
            ["Scorri le <b>card dei servizi</b>: tocca «Richiedi un preventivo» su quella che ti interessa.",
             "In <b>Eventi realizzati</b> filtra le foto per categoria e tocca una foto per ingrandirla; con le frecce passi alla successiva.",
             "In <b>Show demo</b> tocca un video per guardarlo."],
            [("info", "Ogni foto ha una didascalia (evento e data). Le foto nuove compaiono sul sito solo dopo che l'Admin le ha pubblicate.")])
story += [PageBreak()]
story += cl("Configuratore e preventivo", "In pochi tocchi il cliente descrive l'evento e prepara la richiesta di preventivo.", "sito-configuratore",
            "Il configuratore: tipo di evento, numero di ospiti e servizi desiderati.",
            ["Scegli il <b>tipo di evento</b> (matrimonio, festa privata, evento aziendale, concerto, discoteca, altro).", "Indica il <b>numero di ospiti</b> e seleziona i <b>servizi</b> che ti servono.",
             "Se il titolare ha attivato le tariffe pubbliche vedi una <b>stima indicativa</b> «da € …».",
             "Tocca <b>«Vai al preventivo con queste scelte»</b>: il modulo si apre già compilato."],
            [("attenzione", "La stima è sempre indicativa. Il prezzo definitivo è quello scritto nel preventivo che riceverai.")])
story += [PageBreak()]
story += cl("Prenotare un appuntamento o chiedere un preventivo", "Due moduli affiancati: uno per fissare una chiamata o un incontro, uno per descrivere l'evento e ricevere un preventivo.", "sito-form",
            "A sinistra «Prenota un appuntamento» (con giorno e orario liberi), a destra «Richiedi un preventivo».",
            ["Per prenotare scegli un <b>giorno</b>: gli orari liberi compaiono da soli (i giorni chiusi o pieni non si possono scegliere).", "Compila nome, telefono ed email; la data dell'evento e le note sono facoltative.",
             "Leggi la riga di informativa, spunta la <b>presa visione della privacy</b> e premi «Conferma appuntamento» o «Invia richiesta».",
             "Riceverai una conferma e, il giorno prima, un promemoria: puoi spostare o annullare dal link nell'email."],
            [("info", "Per rispondere ti servono solo i dati necessari: li conserviamo 24 mesi e non li cediamo a terzi (dettagli nell'informativa privacy).")])
story += [PageBreak()]
story += cl("Contatti, emergenza 24 ore e assistente AI", "Telefono, WhatsApp, email, social e due strumenti per le urgenze: il tasto Emergenza e l'assistente automatico.", "sito-contatti",
            "La sezione Contatti con il team, gli orari, la sede e i social.",
            ["Tocca il <b>numero di telefono</b> per chiamare o <b>WhatsApp</b> per scrivere subito.", "Il tasto rosso <b>«Emergenza 24h»</b> in basso a sinistra apre la finestra per chiamare o lasciare il numero per essere richiamati.",
             "L'<b>assistente LMC AI</b> (icona in basso a destra) risponde a domande su servizi, orari e prenotazioni, anche a voce. È un assistente automatico, non una persona.",
             "In fondo al sito trovi i link a social, informativa privacy e accessibilità."],
            [("sicurezza", "La «Voce naturale» manda l'audio a un servizio esterno (Vapi, USA): il sito te lo dice e chiede conferma prima di partire. La chat scritta e la voce del browser funzionano senza.")])
story += [Spacer(1, 4 * mm)]
story += sez("Recensioni e installazione dell'app", ["CLIENTE"], "Due piccole cose utili: lasciare un parere dopo l'evento e tenere il sito sul telefono come un'app.", [
    d_recensione(), Spacer(1, 2 * mm),
    H2("Lasciare una recensione"), passi(["Dopo l'evento ricevi un'email con un <b>link personale</b> (le email vanno attivate: vedi Parte 6).", "Scegli le stelle, scrivi due righe e conferma di acconsentire alla pubblicazione col tuo nome.",
                                          "La recensione arriva al titolare, che la legge: se la <b>approva</b> compare sul sito con nome, stelle ed evento."], TEAL),
    H2("Installare l'app sul telefono"),
    tabella([["Telefono", "Come si fa"], ["iPhone (Safari)", "Tocca Condividi, poi «Aggiungi a Home». L'icona LMC compare tra le app."],
             ["Android (Chrome)", "Menu a tre puntini, poi «Installa app» o «Aggiungi a schermata Home»."], ["Con il QR", "Inquadra il codice «App clienti» in fondo al libretto o sui materiali stampati."]],
            [40 * mm, 134 * mm])])
story += [PageBreak()]
story += cl("Privacy, cookie e accessibilità", "Il sito è costruito per rispettare i dati e l'accessibilità: le regole sono scritte in due pagine facili da trovare in fondo.", "sito-privacy",
            "L'informativa privacy: chi tratta i dati, quali, perché e per quanto tempo, e come esercitare i propri diritti.",
            ["<b>Privacy e cookie</b>: il sito usa solo un cookie tecnico di sessione, nessun cookie di marketing e nessun contenuto incorporato da altri siti. Per questo non compare un banner di scelta.",
             "<b>Diritti</b>: puoi chiedere accesso, correzione o cancellazione dei dati scrivendo all'indirizzo indicato nell'informativa.",
             "<b>Accessibilità</b>: il sito si usa da tastiera, ha sottotitoli sul video, contrasti leggibili e rispetta l'opzione «riduci animazioni» del dispositivo.",
             "Le due pagine sono nel piè di pagina: «Informativa privacy e cookie» e «Accessibilità»."],
            [("info", "I dati delle richieste vengono resi anonimi automaticamente dopo 24 mesi; le fatture si conservano 10 anni per legge.")])


# ============================================================ PARTE 3 · ADMIN
def ad(titolo_, scopo, stem, leg, passi_=None, note_=None, extra=(), ruoli=("ADMIN",), did=None, key=None, intro_extra=(), wd=None):
    o = sez(titolo_, list(ruoli), scopo, intro_extra, key)
    o.append(schermata(SHOTS, stem, leg, ROSSO, did or "Schermata di esempio con dati di prova: i numeri rossi corrispondono alla legenda.", wd=wd or (108 * mm if extra else None)))
    o.append(Spacer(1, 2 * mm))
    if passi_:
        o += [H2("Come si fa"), passi(passi_)]
    for n in (note_ or []):
        o += [Spacer(1, 2 * mm), nota(n[1], n[0])]
    if extra:
        o.append(KeepTogether(list(extra)))
    return o


story += PT(3, "Il gestionale\nper l'Admin", "Ogni schermata del pannello, una per una:\na cosa serve, dove cliccare e cosa controllare.",
            ["Accesso e sicurezza", "Dashboard, agenda e richieste", "Preventivi, fatture e acconti", "Clienti, materiale ed eventi", "Galleria e recensioni",
             "Testi, tariffe e statistiche", "WhatsApp, utenti, registro e backup"], ROSSO)
login_img = img(SHOTS, "admin-login", "desktop", 70 * mm)
story += sez("Accesso e sicurezza", ["ADMIN", "COLLABORATORE"], "Il gestionale è un'area riservata: si apre dal telefono o dal computer, come un'app.", [
    Table([[cornice(login_img) if login_img else "", [H2("Come si entra"), passi([
        "Apri <font name='Mono'>/admin</font> dopo l'indirizzo del sito, oppure inquadra il QR «Accesso Admin» in fondo al libretto.",
        "Scrivi <b>utente</b> e <b>password</b> e premi «Accedi».",
        "La <b>prima volta</b> il sistema ti chiede di scegliere una password tua: almeno 10 caratteri, che non usi altrove.",
        "Per installarlo come app: dal menu del browser scegli «Aggiungi a schermata Home».",
        "Per uscire usa sempre <b>«Esci»</b> in alto a destra, soprattutto su telefoni condivisi."])]]],
          colWidths=[74 * mm, CW - 74 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("LEFTPADDING", (1, 0), (1, 0), 6 * mm)]),
    Spacer(1, 4 * mm),
    tabella([["Protezione", "Come funziona"],
             ["Blocco dei tentativi", "Dopo 5 password sbagliate il login si blocca per 5 minuti."],
             ["Password temporanea", "Chi riceve una password dall'Admin deve cambiarla al primo accesso."],
             ["Ruoli", "L'Admin vede tutto; il collaboratore solo il lavoro operativo. Il server blocca le pagine vietate."],
             ["Sessione", "Il collegamento è cifrato (HTTPS) e protetto contro invii non voluti (CSRF)."],
             ["Registro attività", "Accessi e azioni sensibili restano scritti: chi, cosa, quando."]], [46 * mm, 128 * mm]),
    Spacer(1, 3 * mm),
    nota("Non condividere mai la tua password e non scriverla in email o chat. Per un collaboratore crea un <b>account personale</b> (capitolo Utenti): così ogni azione ha un nome.", "sicurezza")])
story += [PageBreak()]
story += ad("Dashboard", "La pagina da aprire ogni mattina: cosa succede oggi e cosa aspetta una risposta.", "admin-dashboard",
            ["<b>Menu laterale</b>: tutte le sezioni (su telefono si apre dal pulsante in alto). Mostra solo ciò che il tuo ruolo può usare.",
             "<b>Schede riepilogo</b>: appuntamenti di oggi, richieste da gestire, incassi del mese, importo ancora da incassare (con le fatture scadute) ed eventi dei prossimi 30 giorni. Toccane una per aprire la pagina.",
             "<b>Appuntamenti di oggi</b>: orario, cliente e stato.", "<b>Richieste nuove</b>: preventivi e appuntamenti da confermare con i pulsanti <i>Conferma</i> e <i>Annulla</i>.",
             "<b>Eventi in arrivo</b> e <b>Da fare</b>: i lavori dei giorni successivi e le cose rimaste in sospeso."],
            ["Guarda le schede in alto: i numeri in rosso (richieste, fatture scadute) sono quelli che richiedono un'azione.", "Conferma o annulla direttamente dalla Dashboard: il cliente riceve la risposta (con le email attive).",
             "Dopo aver confermato un appuntamento compare l'invito a creare la <b>fattura</b> e l'<b>acconto</b>."],
            [("consiglio", "Il collaboratore vede la stessa Dashboard, ma senza le schede degli incassi.")])
story += [PageBreak()]
story += ad("Agenda", "Il calendario mensile con i giorni colorati. È collegato alla disponibilità mostrata sul sito: se blocchi un giorno qui, i clienti non lo possono prenotare.", "admin-agenda",
            ["<b>Calendario del mese</b>: ogni giorno ha un colore: <i>libero</i> (verde), <i>impegnato</i> (rosso), <i>da confermare</i> (giallo), <i>bloccato</i> (grigio a righe), <i>non lavorativo</i> (scuro). Le frecce cambiano mese.",
             "<b>Dettaglio del giorno</b> scelto: appuntamenti con <i>Conferma</i>, <i>Annulla</i>, <i>WhatsApp</i> e <i>Fattura</i>; sotto <i>Azioni rapide</i>: <b>Blocca il giorno</b> con un motivo (ferie, evento già pieno) e <b>Note del giorno</b> (appunti interni)."],
            ["Tocca un giorno nel calendario: a destra compare il dettaglio.", "Per chiudere un giorno scrivi il motivo e premi <b>«Blocca il giorno»</b>; per riaprirlo premi «Sblocca il giorno».",
             "Scrivi appunti per il team nelle <b>Note del giorno</b> e premi «Salva nota»: si vede chi ha modificato per ultimo.", "Gli orari fissi e le chiusure ricorrenti si impostano da «Orari e giorni di chiusura ricorrenti»."],
            [("info", "Il cliente riceve un promemoria email il giorno prima di ogni appuntamento confermato (con le email attive).")], ruoli=("ADMIN", "COLLABORATORE"))
story += [PageBreak()]
story += ad("Richieste", "Qui arrivano i moduli compilati sul sito: appuntamenti e preventivi. Da qui parte tutto il flusso della pratica.", "admin-richieste",
            ["<b>Tabella Appuntamenti</b>: quando, cliente (con telefono ed email), evento, stato. Cambia lo stato dal menu e premi <i>Salva</i>.",
             "<b>Riepilogo</b>: invia su WhatsApp un riepilogo della richiesta alla persona «di turno» (o a un numero che scegli). Richiede Twilio attivo: altrimenti il sito te lo segnala.",
             "<b>Fai il preventivo</b>: apre la pagina Preventivi già collegata al cliente. Nella stessa riga <i>+ Cliente</i> crea la scheda anagrafica."],
            ["Apri Richieste: le nuove sono in evidenza.", "Leggi i dettagli (evento, data, luogo, servizi, note) e chiama o scrivi al cliente.",
             "Cambia lo stato: per gli appuntamenti <i>in attesa, confermato, annullato, completato</i>; per i preventivi <i>nuova, in lavorazione, inviata, chiusa</i>.",
             "Con <b>«Fai il preventivo»</b> prepari l'offerta; con <b>«Fattura»</b> sull'appuntamento passi direttamente alla fatturazione."],
            [("consiglio", "Il cliente può spostare o annullare un appuntamento da solo, dal link ricevuto per email.")], ruoli=("ADMIN", "COLLABORATORE"))
story += [PageBreak()]
story += ad("Preventivi", "Prepara l'offerta per il cliente con i prezzi del listino e scaricala in PDF.", "admin-preventivi",
            ["<b>Nuovo preventivo</b>: scegli il cliente, aggiungi una nota, inserisci le righe (descrizione, quantità, prezzo) a mano oppure con <i>+ dal listino tariffe</i>. Il totale (IVA esclusa) si calcola da solo.",
             "<b>Elenco</b>: numero, cliente, totale, acconti già versati e stato. A destra: <i>PDF</i>, <i>+ Acconto</i>, <i>Fattura</i> (trasforma il preventivo in fattura) ed elimina."],
            ["Premi <b>«Fai il preventivo»</b> da Richieste, oppure scegli un cliente e compila le righe.", "Controlla il totale e premi «Crea preventivo»: ottieni un numero (es. P2026-001).",
             "Scarica il <b>PDF</b> e invialo al cliente. Metti lo stato su <i>inviato</i>.", "Quando il cliente accetta metti <i>accettato</i> e premi <b>«Fattura»</b>: cliente e importi sono già compilati."],
            [("info", "Stati del preventivo: bozza, inviato, accettato, rifiutato. Un preventivo accettato si può trasformare in fattura una volta sola.")])
story += [PageBreak()]
story += ad("Fatture", "Fatture di cortesia in PDF con i dati della tua azienda. Il numero progressivo si assegna solo quando EMETTI: niente buchi nella numerazione.", "admin-fatture",
            ["<b>+ Nuova fattura</b> (vuota) oppure da richiesta o preventivo. Vicino c'è <i>Dati fiscali e numerazione</i> (vedi sotto). In alto: fatturato, incassato, da incassare e fatture scadute dell'anno.",
             "<b>Elenco</b>: numero, cliente, data, scadenza, totale, residuo, <b>stato</b>, stato SDI e PDF. Il filtro sopra mostra solo bozze, emesse, parziali, scadute, pagate o annullate."],
            ["Crea la fattura: resta in <b>bozza</b> e senza numero. Controlla voci, imponibile e IVA.", "Premi <b>«Emetti»</b>: il sistema assegna il numero (es. F2026-001) e la data. Da quel momento non si modifica più.",
             "Scarica il <b>PDF</b> e invialo al cliente. Se serve la fattura elettronica usa il tuo software o il commercialista (vedi nota).", "Registra i pagamenti in Acconti: lo stato si aggiorna da solo."],
            [("attenzione", "Il PDF è una <b>copia di cortesia</b>: l'XML per il Sistema di Interscambio (SDI) non viene generato. Lo stato SDI si segna a mano.")],
            )
story += [PageBreak()]
story += ad("La singola fattura e i dati fiscali", "La pagina di una fattura emessa: dati, incassi, stato SDI. Prima di emettere la prima fattura compila i dati fiscali.", "admin-fattura",
            ["<b>Dati</b>: cliente, date, imponibile, IVA, totale, incassato e residuo, con le voci.", "<b>Acconti e incassi</b>: elenco dei pagamenti ricevuti per questa fattura.",
             "<b>Registra incasso</b>: importo, data, metodo (bonifico, contanti, carta, assegno, altro) e nota.", "<b>Segna come pagata</b>: registra in un colpo solo il residuo e chiude la fattura."],
            ["In alto trovi i pulsanti: <b>PDF</b>, <i>Segna come pagata</i>, <i>Annulla fattura</i> (il numero resta tracciato e non si riusa), <i>Elenco</i>.", "Per un pagamento parziale usa «Registra incasso»: la fattura diventa <i>parziale</i>.",
             "Più in basso puoi segnare lo <b>stato SDI</b> (non inviata, inviata, consegnata, scartata, mancata consegna) con una nota."],
            extra=[Spacer(1, 3 * mm), H2("Dati fiscali e numerazione (Fatture › Dati fiscali)"),
                   tabella([["Campo", "A cosa serve"], ["Ragione sociale, P.IVA, codice fiscale, sede legale", "Compaiono nell'intestazione di ogni fattura e preventivo (da compilare con i dati reali)."],
                            ["IBAN, PEC, codice SDI", "IBAN per i bonifici in fondo al PDF; PEC e codice destinatario per la fattura elettronica."],
                            ["Prefisso, prossimo numero, cifre, azzeramento annuale", "Costruiscono il numero: es. «F» + anno + progressivo a 3 cifre (F2026-001). Si può far ripartire da 1 ogni anno."],
                            ["IVA predefinita, scadenza in giorni, dicitura di regime, nota a piè", "Valori proposti a ogni nuova fattura (es. IVA 22%, scadenza 30 giorni, dicitura forfettario)."]], [66 * mm, 108 * mm]),
                   Spacer(1, 2 * mm), nota("I dati fiscali veri (P.IVA, sede, IBAN) li inserisce il titolare: nel libretto e negli esempi sono dati di prova.", "attenzione")])
story += [PageBreak()]
story += ad("Acconti e incassi", "Registri ogni pagamento ricevuto, anche a rate. Il sistema calcola il residuo e aggiorna lo stato della fattura.", "admin-acconti",
            ["<b>Contatori</b>: incassato nel mese e nell'anno. Sono la somma dei pagamenti registrati: è l'unico modo per avere numeri esatti.",
             "<b>Registra un pagamento</b>: scegli a cosa si riferisce (preventivo, fattura o evento), importo, data, metodo e nota, poi «Registra»."],
            ["Apri Acconti: sotto il modulo c'è la <b>Situazione pratiche</b> con totale, versato, residuo e stato (da versare, parziale, pagata, scaduta).", "Scegli la pratica, scrivi l'importo ricevuto e il metodo, premi «Registra».",
             "Se il versato è minore del totale lo stato è <i>parziale</i>; quando arriva al totale la fattura diventa <i>pagata</i>.", "Un pagamento sbagliato si elimina dalla riga (resta scritto nel Registro attività)."],
            [("consiglio", "Registra l'acconto appena lo ricevi: la Dashboard e le Statistiche si aggiornano subito.")])
story += [PageBreak()]
story += sez("Clienti, materiale, eventi e assistente", ["ADMIN", "COLLABORATORE"], "Le voci del menu che sostengono il lavoro quotidiano: anagrafica, attrezzatura, calendario dei lavori e registro delle chiamate.", [
    tabella([["Voce", "A cosa serve", "Campi principali", "Chi"],
             ["Clienti", "Anagrafica per preventivi e fatture. Si crea anche da una richiesta con «+ Cliente».", "Nome, telefono, email, indirizzo, P.IVA, codice fiscale, codice SDI, PEC, note", "Admin"],
             ["Materiale", "Elenco delle attrezzature (audio, luci, video) e di quante ne hai.", "Attrezzatura, categoria, quantità, stato (disponibile, in uso, in riparazione, fuori servizio), note", "Admin e collaboratore"],
             ["Eventi", "Calendario dei lavori confermati. Ad ogni evento si assegna l'attrezzatura: il sistema controlla le quantità disponibili.", "Titolo, data, luogo, tipo, stato (confermato, svolto, annullato), cliente, note", "Admin e collaboratore"],
             ["Assistente e chat", "Registro delle chiamate dell'assistente vocale, dei riepiloghi della chat e delle richieste di emergenza.", "Orario, numero, riepilogo o trascrizione", "Admin e collaboratore"]],
            [26 * mm, 62 * mm, 62 * mm, 24 * mm]), Spacer(1, 3 * mm),
    H2("Come si usano"), passi(["<b>Materiale</b>: aggiungi ogni attrezzatura con la quantità e tieni aggiornato lo <i>stato</i>: se qualcosa va in riparazione segnalo subito, così non lo assegni a un evento.",
                                "<b>Eventi</b>: crea l'evento, scegli il cliente e assegna l'attrezzatura. Il sistema segnala se la quantità richiesta non è disponibile.",
                                "<b>Assistente e chat</b>: guarda ogni giorno le richieste di richiamo e le emergenze arrivate fuori orario.",
                                "<b>Clienti</b>: se la richiesta arriva da un nuovo cliente premi «+ Cliente» in Richieste: i dati si copiano da soli."]),
    Spacer(1, 3 * mm), nota("Le chiamate e i riepiloghi dell'assistente si conservano 12 mesi, poi vengono cancellati in automatico.", "info")])
story += [PageBreak()]
story += ad("Galleria eventi", "Le foto e i video dei lavori. Ogni foto ha una didascalia obbligatoria e parte nascosta: la pubblichi solo quando sei sicuro.", "admin-galleria",
            ["<b>Carica foto e video</b>: didascalia (obbligatoria), tipo di evento, data, categoria sul sito, evento o fattura collegati. Foto fino a 12 MB e video fino a 60 MB; le immagini vengono ottimizzate da sole.",
             "<b>Elenco delle foto</b>: ogni scheda mostra lo stato (pubblicata o nascosta) e i pulsanti per pubblicare, nascondere, modificare ed eliminare. Si riordinano trascinando."],
            ["Premi «Carica» e scegli i file dal telefono o dal computer.", "Scrivi la <b>didascalia</b> (cosa è, quale evento) e scegli tipo ed evento: senza didascalia non si carica.",
             "Le foto nuove sono nelle <b>Nascoste</b> (bozze): nessuno le vede sul sito.", "Controlla l'anteprima e premi <b>«Pubblica»</b>: da quel momento compaiono in galleria e in home. «Nascondi» le toglie."],
            [("regola", "Il collaboratore può caricare ma <b>non pubblicare né eliminare</b>: la pubblicazione è una decisione dell'Admin.")],
            extra=[Spacer(1, 3 * mm), d_galleria()], ruoli=("ADMIN", "COLLABORATORE"))
story += [PageBreak()]
story += ad("Recensioni", "Chiedi un parere al cliente dopo l'evento e scegli tu cosa pubblicare. Una recensione non compare mai sul sito senza la tua approvazione.", "admin-recensioni",
            ["<b>Chiedi una recensione</b>: scegli un evento o un appuntamento (oppure scrivi nome ed email), indica come comparirà l'evento e premi «Invia richiesta». Il cliente riceve un link personale. Sotto puoi attivare l'invio automatico il giorno dopo l'evento.",
             "Nelle schede in alto: <i>Da approvare</i>, <i>Pubblicate</i>, <i>Richieste inviate</i>, <i>Rifiutate</i>. Per ogni recensione da approvare puoi correggere nome ed evento e premere «Approva e pubblica» oppure rifiutarla."],
            ["Dopo l'evento parte (se attivata) l'email con il link: il cliente sceglie le stelle e scrive due righe.", "La recensione arriva in <b>Da approvare</b>: leggila, correggi eventuali errori di battitura.",
             "Premi «Approva e pubblica»: compare sul sito con stelle, nome ed evento. Oppure «Rifiuta».", "Per una recensione ricevuta altrove (Google, WhatsApp) usa «Aggiungi una recensione ricevuta altrove»: inserisci solo recensioni vere."],
            [("regola", "Sul sito compaiono <b>solo recensioni approvate</b>: niente recensioni inventate, niente valutazioni false nei dati per Google."), ("info", "L'email del cliente si cancella appena invia la recensione (o dopo 60 giorni senza risposta).")],
            extra=[Spacer(1, 3 * mm), d_recensione()])
story += [PageBreak()]
story += sez("Testi del sito, Team e contatti, Disponibilità", ["ADMIN"], "Tre pagine per tenere aggiornati contenuti, persone e orari senza toccare il codice.", [
    tabella([["Pagina", "Cosa contiene", "Dove compare sul sito"],
             ["Testi del sito", "Identità (nome, titolare, città, data di fondazione), claim e storia, contatti e orari, social, dati societari, informativa privacy (testo e dettagli), servizi (fino a 6), cifre in evidenza, frasi dell'intro.", "Hero, Chi siamo, Contatti, footer, /privacy, intro, assistente"],
             ["Team e contatti", "Persone con ruolo, telefono, email e nota. Per ciascuna: mostrare sul sito, ricevere notifiche, essere «di turno» (riceve riepiloghi ed emergenze).", "Sezione Contatti e assistente"],
             ["Disponibilità (Orari e chiusure)", "Fasce settimanali (giorno, dalle alle), giorni di chiusura (ferie, festivi) e durata di ogni appuntamento.", "Giorni e orari prenotabili sul sito"]],
            [38 * mm, 90 * mm, 46 * mm]), Spacer(1, 3 * mm),
    H2("Cose da controllare"), passi(["In <b>Testi</b> salva con «Salva tutto»: un campo che non è nel modulo non viene mai azzerato.", "Scrivi nelle <b>Cifre in evidenza</b> solo numeri veri: se resta vuoto il sito non mostra cifre inventate.",
                                      "Tieni almeno <b>una persona «di turno»</b> in Team: è chi riceve le emergenze.", "In <b>Disponibilità</b> sostituisci gli orari di esempio con quelli reali (di default lun-ven 10-13 e 16-19)."]),
    Spacer(1, 3 * mm), nota("I dati societari (ragione sociale, P.IVA, sede) e l'informativa privacy si completano qui: compaiono nel piè di pagina e nei PDF.", "attenzione")])
story += [PageBreak()]
story += ad("Tariffe (listino base)", "I prezzi di partenza usati per preparare preventivi e fatture e, se vuoi, per la stima nel configuratore del sito.", "admin-tariffe",
            ["<b>Nuova voce</b>: nome, categoria (audio, luci, ledwall e video, allestimenti, personale, trasporto, altro), servizio del sito, unità (a evento, a serata, al mq, all'ora, al giorno, a pezzo), prezzo IVA esclusa e note. «Sul sito (stima)» la rende visibile ai clienti.",
             "<b>Listino</b>: le voci già inserite, modificabili. Le voci a 0 € e disattivate sono segnaposto."],
            ["Scrivi il prezzo di ogni voce e l'unità.", "Attiva le voci che vuoi usare nei preventivi (quelle disattive restano nascoste).", "Per mostrare una stima ai clienti spunta «Mostra nel configuratore…» in alto e marca le voci «Sul sito».",
             "Cambiare un prezzo <b>non</b> modifica i preventivi e le fatture già fatti."],
            [("attenzione", "Compila le tariffe <b>prima</b> di consegnare il gestionale ai collaboratori: i preventivi partono da qui.")])
story += [PageBreak()]
story += ad("Statistiche", "Numeri chiari per capire come va il lavoro, anno per anno. Solo per l'Admin.", "admin-statistiche",
            ["<b>Contatori dell'anno</b>: incassato, richieste ricevute (preventivi e appuntamenti), confermate e percentuale di conversione.", "<b>Incassi per mese</b>: istogramma dai pagamenti registrati.",
             "<b>Eventi per tipo</b>: quanti matrimoni, feste, eventi aziendali, concerti.", "<b>Servizi più richiesti</b>: cosa chiedono più spesso i clienti dal configuratore e dai moduli."],
            ["Cambia anno dai pulsanti in alto (2026, 2025, …).", "Guarda la <b>conversione</b>: quante richieste diventano eventi confermati.", "Confronta gli incassi dei mesi per capire le stagioni migliori.",
             "In fondo trovi anche «Incassi per anno» e «Come hai incassato» (per metodo di pagamento)."],
            [("info", "Gli incassi derivano dai pagamenti registrati in Acconti: se non registri un incasso, non compare qui.")])
story += [PageBreak()]
story += ad("WhatsApp, report e impostazioni", "La pagina di stato di WhatsApp (Twilio) e le Impostazioni dove si inseriscono le chiavi dei servizi esterni.", "admin-whatsapp",
            ["<b>Stato</b>: se Twilio è attivo, messaggi inviati e errori degli ultimi 7 giorni, persone «di turno».", "<b>Cosa viene inviato</b>: avviso a ogni nuovo preventivo o appuntamento, report giornaliero, settimanale e mensile, emergenze e riepiloghi della chat, riepilogo manuale dalle Richieste."],
            ["Apri WhatsApp: se è «Non attivo» nessun avviso parte, ma il sito funziona lo stesso.", "Per attivarlo inserisci le credenziali in <b>Impostazioni › WhatsApp / Twilio</b> e usa i pulsanti «Verifica credenziali» e «Messaggio di prova».",
             "In <b>Team e contatti</b> scegli chi riceve gli avvisi e chi è di turno."],
            [("attenzione", "Oggi WhatsApp non è attivo: l'avviso più semplice da attivare è l'<b>email</b> (vedi Parte 6 e la guida per l'agenzia).")],
            extra=[Spacer(1, 3 * mm), H2("Impostazioni: i servizi esterni"),
                   tabella([["Scheda", "Cosa contiene", "Servizio"], ["WhatsApp / Twilio", "Account SID, token, numero mittente, destinatari, interruttore «avvisa a ogni richiesta».", "Twilio"],
                            ["Assistente vocale", "Chiavi e identificativi dell'assistente, assistente per l'emergenza, segreto del webhook.", "Vapi"],
                            ["Report automatici", "Giornaliero, settimanale, mensile: attivo, orario e destinatari.", "Twilio"],
                            ["Emergenza 24h", "Pulsante rosso attivo sì/no, numero da chiamare, orari di risposta.", "-"]], [38 * mm, 112 * mm, 24 * mm])], wd=96 * mm)
story += [PageBreak()]
story += ad("Utenti e permessi", "Qui decidi chi può entrare e cosa può fare. Due ruoli: Admin (tutto) e Collaboratore (solo il lavoro operativo).", "admin-utenti",
            ["<b>Nuovo utente</b>: nome utente per l'accesso, nome e cognome, email, ruolo e password iniziale (se la lasci vuota la genera il sistema).", "<b>Cosa può fare ciascun ruolo</b>: la tabella dei permessi, sempre consultabile. Più in basso l'elenco degli utenti con ultimo accesso e stato."],
            ["Premi «Crea utente»: il sistema mostra la <b>password temporanea</b> una sola volta. Comunicala a voce o con un messaggio privato.", "Al primo accesso la persona deve cambiarla.",
             "Per sospendere qualcuno senza cancellarlo premi <b>«Disattiva»</b>: non potrà più entrare, ma la sua storia resta nel registro.", "«Reset password» genera una nuova password temporanea; il menu «Ruolo» e «Salva» cambiano il ruolo."],
            [("sicurezza", "Un account per ogni persona: mai condividere un solo accesso. L'ultimo Admin non si può disattivare né declassare."), ("consiglio", "Quando un collaboratore smette di lavorare con te, disattiva subito il suo account.")])
story += [PageBreak()]
story += ad("Registro delle attività", "Chi ha fatto cosa e quando: la memoria di tutte le azioni sensibili. Solo l'Admin lo legge.", "admin-registro",
            ["<b>Tabella</b>: data e ora (UTC), utente, ruolo, azione (accesso, fattura emessa, acconto registrato, foto caricate, accesso negato…), dettagli e indirizzo IP. In alto i filtri per utente e per azione."],
            ["Apri Registro: vedi le ultime 300 azioni.", "Filtra per <b>utente</b> o scrivi una parola nell'azione (es. «fattura»).", "Controlla gli «Accesso negato»: indicano che qualcuno ha provato ad aprire una pagina non consentita."],
            [("sicurezza", "Le password e i token non vengono mai scritti nel registro."), ("info", "Il registro è una prova utile in caso di dubbi: chi ha emesso o annullato una fattura, chi ha cancellato una foto.")])
story += [PageBreak()]
story += ad("Backup e sicurezza dei dati", "Il database e i file vengono copiati ogni notte in modo cifrato, sul server e su uno spazio cloud esterno. Qui controlli che sia andato tutto bene.", "admin-backup",
            ["<b>Stato</b>: esito dell'ultimo backup, data e ora, quante ore fa, esito della copia sul cloud e nome dell'archivio più recente.", "<b>Come funziona</b>: ogni notte alle 03:20 il server salva database, foto, video e impostazioni, cifrati; una seconda copia, cifrata e verificata, va su uno spazio cloud esterno al server; se qualcosa non va arriva un'email."],
            ["Apri Backup ogni tanto: deve dire <b>OK</b> con un orario recente (di stamattina).", "Se la data è più vecchia di un giorno, avvisa chi gestisce il server.",
             "Prima di ogni aggiornamento del sito lo script controlla il backup e fa una copia di sicurezza."],
            [("attenzione", "Il <b>ripristino</b> di un backup non si fa dal gestionale: serve un tecnico (script di ripristino sul server)."), ("sicurezza", "La password di cifratura dei backup è sul server: <b>salvane una copia fuori dal server</b> (altrimenti i backup non si possono riaprire).")],
            extra=[Spacer(1, 3 * mm), d_backup()])
story += [PageBreak()]
mob = [img(SHOTS, s, "mobile", 38 * mm) for s in ("admin-dashboard", "admin-agenda", "admin-richieste", "admin-collab-dashboard")]
story += sez("Anche da telefono", ["ADMIN", "COLLABORATORE"], "Il gestionale si adatta allo schermo: stesse funzioni, menu a scomparsa. Si può installare come app.", [
    Table([[cornice(m) for m in mob if m]], colWidths=[(CW) / 4] * len([m for m in mob if m]), style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]),
    Paragraph("Da sinistra: Dashboard, Agenda, Richieste (Admin) e Dashboard del collaboratore.", cap), Spacer(1, 3 * mm),
    H2("Consigli per l'uso da telefono"), passi(["Il <b>menu</b> si apre dal pulsante in alto a sinistra e si chiude toccando fuori.", "Le tabelle larghe (richieste, fatture) si scorrono con il dito, in orizzontale.",
                                                  "Per la <b>galleria</b> scatta o scegli le foto direttamente dal telefono: sono più comode da caricare subito dopo l'evento.", "Esci sempre con «Esci» se il telefono lo usa anche altra gente."]),
    Spacer(1, 3 * mm), nota("Se installi il gestionale come app, ricordati che l'accesso resta attivo: blocca il telefono con un codice.", "sicurezza")])

# ============================================================ PARTE 4 · COLLABORATORI
def co(titolo_, scopo, stem, leg, passi_, note_=None, extra=()):
    o = sez(titolo_, ["COLLABORATORE"], scopo)
    o.append(schermata(SHOTS, stem, leg, AMBRA, "Schermata di esempio: i numeri corrispondono alla legenda.", wd=108 * mm if extra else None))
    o.append(Spacer(1, 2 * mm))
    o += [H2("Come si fa"), passi(passi_, AMBRA)]
    for n in (note_ or []):
        o += [Spacer(1, 2 * mm), nota(n[1], n[0])]
    if extra:
        o.append(KeepTogether(list(extra)))
    return o


story += PT(4, "Per i\ncollaboratori", "Tutto quello che serve a chi lavora ogni giorno con il titolare:\naccesso, giornata tipo, foto, regole d'oro.",
            ["Benvenuto e primo accesso", "Il tuo menu: cosa vedi e cosa no", "La giornata tipo", "Agenda e richieste", "Caricare le foto di un evento", "Regole d'oro e domande frequenti", "Scheda rapida"], AMBRA)
story += sez("Benvenuto e primo accesso", ["COLLABORATORE"], "Il titolare ti ha creato un account personale. Ecco come entrare la prima volta e scegliere la tua password.", [
    Table([[cornice(login_img) if login_img else "", [H2("Il primo accesso"), passi([
        "Apri l'indirizzo del gestionale (o inquadra il QR «Accesso Admin» che ti ha dato il titolare).", "Scrivi il <b>nome utente</b> e la <b>password temporanea</b> ricevuta.",
        "Il sistema ti chiede di scegliere una <b>password tua</b>: almeno 10 caratteri.", "Dopo la nuova password sei dentro: ti aspetta la Dashboard.", "Quando finisci usa <b>«Esci»</b> in alto a destra."], AMBRA)]]],
          colWidths=[74 * mm, CW - 74 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("LEFTPADDING", (1, 0), (1, 0), 6 * mm)]),
    Spacer(1, 4 * mm),
    nota("Per cambiare la password in qualsiasi momento usa l'icona della chiave in alto a destra. Se la dimentichi, chiedi al titolare di fare «Reset password».", "info"), Spacer(1, 2.5 * mm),
    nota("Non scrivere la password su un foglio lasciato in giro e non darla a nessuno, nemmeno ai colleghi: ogni tua azione viene registrata a tuo nome.", "sicurezza"), Spacer(1, 2.5 * mm),
    nota("Se sbagli la password 5 volte il login si blocca per 5 minuti: aspetta e riprova con calma.", "attenzione")])
story += [PageBreak()]
story += co("Il tuo menu: cosa vedi e cosa no", "Il menu del collaboratore ha solo gli strumenti del lavoro quotidiano. Le parti economiche e di gestione restano riservate al titolare.", "admin-collab-dashboard",
            ["<b>Il tuo menu</b>: Dashboard, Agenda, Richieste, Galleria, Materiale, Eventi, Assistente e chat.", "<b>Schede riepilogo</b>: appuntamenti di oggi, richieste da gestire, eventi in arrivo. Non ci sono incassi né fatture.", "<b>Appuntamenti di oggi</b>: orario, cliente, stato."],
            ["Ogni mattina apri la Dashboard e guarda le tre schede in alto.", "Scorri gli <b>appuntamenti di oggi</b> e le <b>richieste nuove</b> in basso.",
             "Se provi ad aprire una pagina non tua compare «Accesso non consentito»: è normale, non hai sbagliato niente."],
            extra=[Spacer(1, 3 * mm), tabella([["Puoi", "Non puoi (chiedi al titolare)"],
                                               ["Vedere e confermare appuntamenti e richieste", "Vedere o creare fatture, preventivi e acconti"], ["Bloccare un giorno e scrivere le note in agenda", "Vedere incassi, statistiche e tariffe"],
                                               ["Caricare foto (restano nascoste)", "Pubblicare o eliminare foto"], ["Consultare materiale ed eventi e le chiamate dell'assistente", "Gestire utenti, impostazioni, backup e recensioni"]], [87 * mm, 87 * mm])])
story += [PageBreak()]
story += sez("La giornata tipo", ["COLLABORATORE"], "Un'abitudine semplice in tre momenti: così nessuna richiesta resta ferma.", [
    d_giornata(), Spacer(1, 4 * mm),
    H2("Checklist del mattino (5 minuti)"), tabella([["Controllo", "Dove", "Se vedi questo"],
                                                      ["Appuntamenti di oggi", "Dashboard", "Controlla orario e telefono del cliente; se manca qualcosa scrivi una nota in Agenda."],
                                                      ["Richieste nuove", "Dashboard › Richieste", "Conferma o annulla quelle chiare; le dubbie falle vedere al titolare."],
                                                      ["Note del giorno", "Agenda", "Leggi gli appunti lasciati da chi c'era prima di te."],
                                                      ["Materiale in riparazione", "Materiale", "Non assegnarlo a un evento finché non è di nuovo disponibile."]], [46 * mm, 38 * mm, 90 * mm]),
    Spacer(1, 3 * mm), nota("Se una richiesta è urgente (evento nei prossimi giorni) chiama il cliente: il telefono è nella scheda della richiesta.", "consiglio")])
story += [PageBreak()]
story += co("Agenda e richieste in pratica", "Il calendario è condiviso con il sito: quello che segni qui decide i giorni che i clienti possono prenotare.", "admin-collab-agenda",
            ["<b>Calendario</b>: tocca un giorno per aprirlo. Verde = libero, rosso = impegnato, giallo = da confermare, grigio = bloccato.", "<b>Dettaglio del giorno</b>: gli appuntamenti con <i>Conferma</i>, <i>Annulla</i> e <i>WhatsApp</i>; sotto <i>Blocca il giorno</i> e le <i>Note del giorno</i>."],
            ["Apri il giorno e controlla gli appuntamenti: se il cliente ha confermato per telefono premi <b>«Conferma»</b>.", "Se il giorno non è disponibile (ferie, evento già pieno) scrivi il motivo e premi <b>«Blocca il giorno»</b>.",
             "Scrivi nelle <b>Note del giorno</b> tutto ciò che serve al team (es. «controllare le batterie dei radiomicrofoni») e premi «Salva nota».", "In <b>Richieste</b> aggiorna lo stato man mano che senti il cliente."],
            [("regola", "Prima di annullare un appuntamento confermato parla con il titolare: il cliente riceve un'email di annullamento.")])
story += [PageBreak()]
story += co("Caricare le foto di un evento", "Le foto dei lavori sono il miglior biglietto da visita. Tu le carichi, il titolare decide quali pubblicare.", "admin-collab-galleria",
            ["<b>Carica foto e video</b>: didascalia obbligatoria, tipo ed evento. Premi «Carica (nascoste)»."],
            ["Apri <b>Galleria</b> e tocca «Scegli file»: puoi selezionarne molti insieme.", "Scrivi la <b>didascalia</b> (es. «Matrimonio al Castello: palco e luci scenografiche»), il tipo di evento e la data.",
             "Premi <b>«Carica (nascoste)»</b>: le foto partono come bozze e <b>nessuno le vede sul sito</b>.", "Avvisa il titolare: sarà lui a controllarle e a premere «Pubblica»."],
            [("attenzione", "Carica solo foto di cui hai il diritto di usare l'immagine e dove i volti non creano problemi: in caso di dubbio chiedi prima."), ("info", "Le foto si ottimizzano da sole: non serve ridimensionarle. Massimo 12 MB per foto e 60 MB per video.")],
            extra=[Spacer(1, 3 * mm), d_galleria()])
story += [PageBreak()]
story += sez("Regole d'oro e domande frequenti", ["COLLABORATORE"], "Cinque regole da ricordare sempre e le risposte alle domande più comuni.", [
    tabella([["Regola", "Perché"], ["1. Un account per persona, password mai condivisa", "Ogni azione è registrata a tuo nome."], ["2. Esci sempre dal gestionale a fine lavoro", "Evita che altri usino il tuo accesso."],
             ["3. Foto: carichi tu, pubblica il titolare", "La pubblicazione è una decisione del titolare."], ["4. Dati dei clienti solo per lavoro", "Nomi, telefoni ed email sono riservati: non copiarli altrove."],
             ["5. Nel dubbio chiedi", "È meglio una domanda in più che una cancellazione sbagliata."]], [90 * mm, 84 * mm]),
    Spacer(1, 4 * mm), H2("Domande frequenti"),
    tabella([["Domanda", "Risposta"],
             ["Non trovo Fatture o Acconti.", "È normale: sono riservate al titolare."], ["Ho dimenticato la password.", "Chiedi al titolare di fare «Reset password»: ti darà una password temporanea."],
             ["Il login non funziona.", "Dopo 5 errori si blocca 5 minuti. Aspetta e riprova; controlla maiuscole e minuscole."], ["La foto non compare sul sito.", "Le foto partono nascoste: deve pubblicarla il titolare."],
             ["Ho sbagliato a confermare un appuntamento.", "Avvisa subito il titolare: può correggere lo stato e avvisare il cliente."], ["Un cliente chiede di cancellare i suoi dati.", "Non farlo tu: passa la richiesta al titolare."]], [64 * mm, 110 * mm])])
story += [PageBreak()]
sc = Table([[Paragraph("<font name='Mont' size=12 color='#ffffff'>1 · ENTRA</font><br/><font color='#ffffff' size=8.6>Indirizzo del gestionale (o QR «Accesso Admin»). Utente e password personali. Esci sempre a fine lavoro.</font>", cell),
             Paragraph("<font name='Mont' size=12 color='#ffffff'>2 · GUARDA</font><br/><font color='#ffffff' size=8.6>Dashboard: appuntamenti di oggi, richieste nuove, eventi in arrivo. Controlla mattina e sera.</font>", cell)],
            [Paragraph("<font name='Mont' size=12 color='#ffffff'>3 · RISPONDI</font><br/><font color='#ffffff' size=8.6>Richieste: leggi, chiama il cliente, cambia lo stato. «Conferma» o «Annulla» solo se sei sicuro.</font>", cell),
             Paragraph("<font name='Mont' size=12 color='#ffffff'>4 · SEGNA</font><br/><font color='#ffffff' size=8.6>Agenda: blocca i giorni non disponibili e scrivi le note del giorno per il team.</font>", cell)],
            [Paragraph("<font name='Mont' size=12 color='#ffffff'>5 · CARICA</font><br/><font color='#ffffff' size=8.6>Galleria: foto con didascalia. Restano nascoste: le pubblica il titolare.</font>", cell),
             Paragraph("<font name='Mont' size=12 color='#ffffff'>6 · CHIEDI</font><br/><font color='#ffffff' size=8.6>Fatture, incassi, tariffe, utenti: solo il titolare. Nel dubbio chiedi.</font>", cell)]],
           colWidths=[CW / 2, CW / 2], rowHeights=[48 * mm] * 3)
sc.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), TEAL), ("BACKGROUND", (1, 0), (1, 0), ANTRA), ("BACKGROUND", (0, 1), (0, 1), AMBRA), ("BACKGROUND", (1, 1), (1, 1), BLU),
                        ("BACKGROUND", (0, 2), (0, 2), ROSSO), ("BACKGROUND", (1, 2), (1, 2), colors.HexColor("#3a3a44")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("LINEBELOW", (0, 0), (-1, -1), 3, colors.white), ("LINEAFTER", (0, 0), (0, -1), 3, colors.white)]))
story += sez("Scheda rapida del collaboratore", ["COLLABORATORE"], "Una pagina da stampare e tenere vicino al telefono o al computer.", [sc, Spacer(1, 4 * mm), nota("Numero del titolare per le urgenze: ________________________    Indirizzo del gestionale: ________________________", "info")])


# ============================================================ PARTE 5 · SPECIFICHE TECNICHE
def te(titolo_, scopo, righe_extra, key=None):
    return sez(titolo_, ["TECNICO"], scopo, righe_extra, key)


story += PT(5, "Specifiche\ntecniche", "Come è costruito il sistema: architettura, sicurezza, dati,\nbackup, messa online e controlli di qualità.",
            ["Architettura", "Sicurezza", "Dati personali e conservazione", "Messa online e aggiornamento", "Servizi esterni", "Qualità e conformità"], BLU)
story += te("Architettura", "Un'applicazione web Python (Flask) con database SQLite, dietro nginx e gunicorn, su un server IONOS.", [
    d_arch(), Spacer(1, 3 * mm),
    tabella([["Livello", "Tecnologia", "Note"],
             ["Server", "VPS IONOS, Ubuntu 24.04", "Cartella applicazione /srv/lmc, utente di servizio «lmc» con permessi limitati"],
             ["Web", "nginx + certificato Let's Encrypt", "HTTPS, redirect da http, compressione gzip, intestazioni di sicurezza"],
             ["Applicazione", "Flask (Python 3) + gunicorn", "2 processi × 4 thread, servizio systemd «lmc» che riparte da solo"],
             ["Dati", "SQLite in modalità WAL", "Un solo file; file e foto in cartelle dedicate, fuori dal codice"],
             ["Pagine", "HTML (Jinja), CSS e JavaScript senza framework", "PWA: installabile, funziona anche con rete debole"],
             ["PDF", "ReportLab", "Preventivi e fatture; questo libretto"],
             ["Attività di fondo", "Un thread dell'app + cron", "Promemoria, report, richieste di recensione, pulizia dati; backup alle 03:20"]],
            [30 * mm, 60 * mm, 84 * mm])])
story += [PageBreak()]
story += te("Sicurezza", "Protezione a livelli: rete, accesso, permessi e dati. Ogni livello fa il suo lavoro anche se un altro viene superato.", [
    d_sicurezza(), Spacer(1, 3 * mm),
    tabella([["Controllo", "Come è fatto"],
             ["HTTPS e intestazioni", "HTTPS obbligatorio con redirect, HSTS, nosniff, X-Frame-Options, Referrer-Policy e Permissions-Policy (microfono solo per l'assistente)."],
             ["Cookie", "Un solo cookie tecnico «session»: HttpOnly, Secure, SameSite=Lax, 8 ore. Nessun cookie di marketing o di analisi."],
             ["Login", "Password con hash, minimo 10 caratteri, blocco dopo 5 tentativi per 5 minuti, cambio obbligatorio per le password temporanee."],
             ["Permessi (RBAC)", "Elenco chiuso di pagine consentite al collaboratore: tutto il resto è negato dal server. Ruoli Admin e Collaboratore; l'ultimo Admin è protetto."],
             ["CSRF", "Ogni invio di modulo porta un codice di sessione verificato dal server."],
             ["Registro attività", "Ogni azione sensibile registra chi, cosa, quando e da quale IP; password e token mascherati."],
             ["Segreti", "Chiavi e password solo nel file .env (permessi 600) e nelle impostazioni cifrate; mai nel codice."],
             ["Contenuti esterni", "Nessuna risorsa caricata da altri siti: font, immagini e script sono serviti dal sito stesso."]], [40 * mm, 134 * mm])])
story += [PageBreak()]
story += te("Dati personali e conservazione", "Il sistema raccoglie il minimo necessario e cancella da solo ciò che non serve più (art. 5 GDPR).", [
    tabella([["Dato", "Perché", "Quanto si conserva", "Come"],
             ["Richieste di preventivo e appuntamenti", "Rispondere al cliente", "24 mesi (configurabile, minimo 6)", "Nome, telefono, email e note diventano anonimi; la riga resta per le statistiche"],
             ["Fatture e clienti fatturati", "Obbligo fiscale", "10 anni", "Non si cancellano"],
             ["Chiamate e riepiloghi dell'assistente, registro WhatsApp", "Gestire richieste e avvisi", "12 mesi", "Cancellati in automatico"],
             ["Conteggio delle visite", "Statistiche anonime (hash giornaliero, nessun IP)", "26 mesi", "Cancellati in automatico"],
             ["Email per la recensione", "Inviare il link", "Fino all'invio della recensione (max 60 giorni)", "Cancellata appena il cliente invia"],
             ["Registro attività", "Sicurezza e responsabilità", "Ultime 300 azioni visibili", "Solo Admin"]], [48 * mm, 40 * mm, 38 * mm, 48 * mm]), Spacer(1, 3 * mm),
    nota("L'informativa privacy e cookie è alla pagina <font name='Mono'>/privacy</font>; la dichiarazione di accessibilità a <font name='Mono'>/accessibilita</font>. Entrambe sono linkate nel piè di pagina. Il testo è una base tecnica: va fatto rivedere dal consulente privacy.", "attenzione")])
story += [PageBreak()]
story += te("Messa online e aggiornamento", "Un solo comando aggiorna il sito, con backup prima e controllo dopo. Se qualcosa non va, il sito resta com'era.", [
    d_deploy(), Spacer(1, 3 * mm),
    H2("Aggiornare il sito"), codice("sudo bash /srv/lmc/deploy/aggiorna.sh"),
    Paragraph("Lo script fa cinque cose: 1) backup di sicurezza, 2) scarica il codice nuovo (git pull), 3) aggiorna le dipendenze, 4) sistema i permessi e il file del servizio, 5) riavvia e controlla che <font name='Mono'>/health</font> risponda.", body),
    H2("Verificare il server"), codice("bash /srv/lmc/deploy/verifica-online.sh https://lmcservice.duckdns.org"),
    Paragraph("Controlla servizi (lmc, nginx, cron), file .env e permessi, modalità produzione, cookie sicuri, pagine pubbliche, certificato HTTPS, log di avvio e backup. Ogni riga è <b>OK</b>, <b>avviso</b> o <b>problema</b>.", body),
    H2("Altri script utili"),
    tabella([["Script", "A cosa serve"], ["deploy/backup.sh", "Backup manuale (parte da solo ogni notte)"], ["deploy/backup-status.sh", "Stato dell'ultimo backup"],
             ["deploy/restore.sh", "Ripristino di un backup (solo tecnico)"], ["deploy/collega-dominio.sh", "Collega un dominio con HTTPS (vedi guida per l'agenzia)"],
             ["python -m backend.kit_consegna", "Rigenera guide, QR e video della consegna"]], [64 * mm, 110 * mm])])
story += [PageBreak()]
story += te("Servizi esterni", "Il sito funziona da solo; questi servizi si aggiungono per avvisi, voce e backup.", [
    tabella([["Servizio", "A cosa serve", "Stato", "Dati che escono dal server"],
             ["IONOS (VPS)", "Ospita sito, dati e backup locali", "Attivo", "Nessuno (è il server)"],
             ["Let's Encrypt", "Certificato HTTPS, si rinnova da solo", "Attivo", "Solo il nome del sito"],
             ["Spazio cloud (Google Drive)", "Seconda copia dei backup, fuori dal server", "Attivo", "Solo file cifrati (AES-256): illeggibili senza la password di cifratura"],
             ["Server email (SMTP)", "Conferme, promemoria, avvisi, recensioni", "<b>Da attivare</b>", "Email del cliente, solo per le sue comunicazioni"],
             ["Twilio / WhatsApp", "Avvisi al team, report, riepiloghi", "Opzionale (non attivo)", "Nome, telefono e sintesi della richiesta, solo se invii tu"],
             ["Vapi", "Assistente vocale «Voce naturale»", "Opzionale (non attivo)", "Audio della conversazione, solo dopo conferma"],
             ["DuckDNS", "Indirizzo gratuito lmcservice.duckdns.org", "Attivo (provvisorio)", "Nessuno"]], [34 * mm, 58 * mm, 32 * mm, 50 * mm]), Spacer(1, 3 * mm),
    d_email()])
story += [PageBreak()]
story += te("Qualità e conformità", "Prima di ogni aggiornamento girano oltre 640 controlli automatici: se uno fallisce, l'aggiornamento non va in produzione.", [
    tabella([["Controllo", "Cosa verifica", "Verifiche"],
             ["Gestionale e permessi", "Ruoli, accessi vietati al collaboratore, fatture, numerazione, acconti, utenti, registro", "96"],
             ["Sito e interfaccia", "Pagine pubbliche, moduli, prenotazioni, chat, social, team, audio", "41 + 31 + 12 + 18 + 10"],
             ["Foto, intro e galleria", "Foto reali, nessuna foto doppia, intro leggibile e centrata", "24 + 17 + 36 + 12 + 14"],
             ["Grafica e allineamenti", "Bordi rossi del tema, centratura su 6 schermi (360-1920 px), sezione storia", "28 + 1 + 26"],
             ["Conformità", "Privacy, cookie, nessuna terza parte, conservazione dati, recensioni vere, accessibilità WCAG 2.2 AA (axe)", "45"],
             ["Messa online e backup", "Script, servizio, avvio reale con gunicorn, backup, rotazione e ripristino", "55 + 45"],
             ["WhatsApp", "Invio, errori, destinatari, report", "59"],
             ["Kit di consegna", "Guide PDF, QR leggibili, video", "75"]], [48 * mm, 100 * mm, 26 * mm]), Spacer(1, 3 * mm),
    H2("Dove si trova cosa nel progetto"),
    tabella([["Cartella", "Contenuto"], ["app/", "Pagine HTML, stili, JavaScript, immagini del sito e dell'admin"], ["backend/", "Il programma: pubblico, admin, gestionale, fatture, permessi, recensioni, email, conservazione dati"],
             ["deploy/", "Script di installazione, aggiornamento, backup, verifica e servizio"], ["docs/", "Guide, checklist, proposte, schermate"], ["tests/ e tools/", "Controlli automatici e strumenti (screenshot, PDF)"],
             ["data/ (sul server)", "Database, caricamenti e stato dei backup: non è nel codice"]], [34 * mm, 140 * mm])])

# ============================================================ PARTE 6 · PROSSIMI PASSI
story += PT(6, "Prossimi passi\ne manutenzione", "Cosa resta da completare, le abitudini che tengono il sistema\nin ordine e cosa fare se qualcosa non va.",
            ["Cosa resta da completare", "Routine di manutenzione", "Se qualcosa non va", "Glossario"], ROSSO)
story += sez("Cosa resta da completare", ["ADMIN", "TECNICO"], "Il sistema è online e funziona. Queste voci lo rendono completo.", [
    tabella([["#", "Cosa", "Perché", "Chi", "Quando"],
             ["1", "<b>Email del sito (SMTP)</b>", "Senza, nessuna conferma o avviso parte", "Pasquale crea la password per le app; tecnico o agenzia la inserisce", "Subito, 15 minuti"],
             ["2", "Dati fiscali (P.IVA, sede, IBAN)", "Fatture e preventivi completi", "Pasquale", "Prima della prima fattura"],
             ["3", "Tariffe (prezzi del listino)", "I preventivi partono da qui", "Pasquale", "Prima di usare i preventivi"],
             ["4", "Account dei collaboratori", "Un accesso personale per ognuno", "Pasquale (Utenti)", "Quando serve"],
             ["5", "Orari reali in Disponibilità", "I clienti prenotano solo negli orari veri", "Pasquale", "Subito"],
             ["6", "Dominio .it", "Indirizzo professionale e email col dominio", "Pasquale decide; agenzia", "Se aderisce"],
             ["7", "Salvare la password di cifratura dei backup fuori dal server", "Senza, i backup non si riaprono", "Pasquale", "Subito"],
             ["8", "WhatsApp (Twilio) e assistente vocale (Vapi)", "Avvisi immediati e voce naturale", "Opzionale", "Più avanti"],
             ["9", "Rilettura dei sottotitoli del video", "Controllo umano di nomi e parole", "Titolare", "Prima di promuovere il video"]],
            [7 * mm, 52 * mm, 49 * mm, 38 * mm, 28 * mm]), Spacer(1, 3 * mm),
    nota("Il punto 1 si spiega passo per passo nella <b>Guida per l'agenzia</b> (secondo PDF), insieme al dominio .it.", "info")])
story += [PageBreak()]
story += sez("Routine di manutenzione", ["ADMIN"], "Poche abitudini regolari tengono il sistema sano e i dati al sicuro.", [
    tabella([["Quando", "Cosa fare", "Dove"],
             ["Ogni giorno", "Aprire la Dashboard mattina e sera; rispondere alle richieste nuove; controllare le chiamate fuori orario", "Dashboard, Richieste, Assistente e chat"],
             ["Ogni settimana", "Approvare le recensioni; guardare le fatture scadute; controllare che il backup sia di stamattina", "Recensioni, Fatture, Backup"],
             ["Ogni mese", "Rivedere le statistiche e le tariffe; controllare gli account attivi; aggiornare il sito", "Statistiche, Tariffe, Utenti, server"],
             ["Ogni anno", "Rinnovare il dominio (se c'è); controllare che la numerazione delle fatture riparta; rivedere l'informativa privacy", "Registrar, Dati fiscali, /privacy"],
             ["Quando cambia qualcosa", "Disattivare subito gli account di chi lascia il team; cambiare password se un accesso è stato condiviso", "Utenti"]], [30 * mm, 98 * mm, 46 * mm])])
story += [Spacer(1, 4 * mm)]
story += sez("Se qualcosa non va", ["ADMIN", "COLLABORATORE", "TECNICO"], "Le situazioni più comuni e cosa fare.", [
    tabella([["Problema", "Possibile causa", "Cosa fare"],
             ["Non vedo una voce del menu o compare «Accesso non consentito»", "Il tuo ruolo non la prevede", "È normale per il collaboratore. Se serve, chiedi al titolare."],
             ["Il login è bloccato", "5 password sbagliate", "Aspetta 5 minuti. Se hai dimenticato la password, l'Admin fa «Reset password»."],
             ["Non arrivano email", "SMTP non configurato", "Vedi punto 1 di «Cosa resta da completare»."],
             ["Una foto non compare sul sito", "È nascosta o non pubblicata", "Galleria › Pubblica (solo Admin)."],
             ["Un cliente non può prenotare un giorno", "Giorno bloccato, chiuso o pieno", "Agenda › sblocca il giorno o controlla Disponibilità."],
             ["Una fattura non ha il numero", "È ancora una bozza", "Aprila e premi «Emetti»."],
             ["La Dashboard non mostra incassi", "Non sono stati registrati pagamenti", "Registra gli acconti in Acconti."],
             ["Il sito non si apre", "Problema del server", "Il tecnico controlla <font name='Mono'>/health</font> e il log: <font name='Mono'>journalctl -u lmc -n 50</font>."]], [58 * mm, 46 * mm, 70 * mm])])
story += [PageBreak()]
gl = [["Termine", "Significato in parole semplici"],
      ["PWA / App", "Il sito si può installare sul telefono come un'app, con la sua icona."], ["HTTPS (lucchetto)", "Collegamento cifrato: nessuno può leggere o modificare ciò che si scambia."],
      ["VPS", "Il computer remoto (di IONOS) su cui gira il sito."], ["SMTP", "L'«ufficio postale» che spedisce le email del sito."], ["Dominio / DNS", "Il nome del sito (es. .it) e l'elenco che lo collega al server."],
      ["Bozza / Emessa", "Una fattura in bozza non ha numero e si può cambiare; quella emessa ha il numero e non si modifica."], ["SDI", "Il Sistema di Interscambio dell'Agenzia delle Entrate per le fatture elettroniche."],
      ["Backup cifrato", "Copia dei dati chiusa con una password: chi la ruba non può leggerla."], ["RBAC / Ruolo", "Il sistema che decide cosa può fare ogni persona (Admin, Collaboratore)."],
      ["CSRF", "Protezione che impedisce a un altro sito di inviare moduli al posto tuo."], ["WCAG / axe", "Le regole internazionali di accessibilità e lo strumento che le controlla."],
      ["Anonimizzare", "Togliere nome, telefono ed email da un dato: resta il numero, non la persona."], ["Callout", "Il cerchio rosso numerato su una schermata: rimanda alla legenda."]]
story += sez("Glossario", None, "Le parole tecniche usate nel libretto, spiegate semplicemente.", [tabella(gl, [46 * mm, 128 * mm])])
story += [NextPageTemplate("div"), PageBreak(), Fine()]


# ============================================================ COSTRUZIONE
def build():
    from backend import kit_qr
    SHOTS.mkdir(parents=True, exist_ok=True)
    kit_qr.plain("https://lmcservice.duckdns.org", QR1)
    kit_qr.plain("https://lmcservice.duckdns.org/admin/login", QR2)
    doc = DocLib(str(OUT), pagesize=(W, H), leftMargin=M, rightMargin=M, topMargin=28 * mm, bottomMargin=20 * mm, title="Libretto illustrativo LMC Service",
                 author="FiveTech", subject="Sito, App e Gestionale di La Music Company Service")
    fr = Frame(M, 20 * mm, CW, H - 48 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_full = Frame(M, 20 * mm, CW, H - 40 * mm, id="g", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    tmpl = [PageTemplate(id="p0", frames=[fr], onPage=copertina), PageTemplate(id="div", frames=[Frame(M, 20 * mm, CW, H - 40 * mm, id="d", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)])]
    cols = {1: ROSSO, 2: TEAL, 3: ROSSO, 4: AMBRA, 5: BLU, 6: ROSSO}
    nomi = {1: "Parte 1 · Il progetto in breve", 2: "Parte 2 · Per i clienti", 3: "Parte 3 · Gestionale Admin", 4: "Parte 4 · Per i collaboratori", 5: "Parte 5 · Specifiche tecniche", 6: "Parte 6 · Prossimi passi"}
    for n in range(1, 7):
        tmpl.append(PageTemplate(id=f"p{n}", frames=[fr], onPage=make_deco(nomi[n], cols[n])))
    # le pagine «Indice» e «Come leggere» usano il modello della parte 1 (intestazione normale)
    tmpl[0] = PageTemplate(id="p0", frames=[Frame(M, 20 * mm, CW, H - 40 * mm, id="c0")], onPage=copertina)
    tmpl.append(PageTemplate(id="p00", frames=[fr], onPage=make_deco("Introduzione", ROSSO)))
    doc.addPageTemplates(tmpl)
    doc.multiBuild(story, canvasmaker=NumberedCanvas)
    print(OUT)


if __name__ == "__main__":
    build()
