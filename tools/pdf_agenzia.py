"""Genera docs/Guida-Agenzia-LMC.pdf: guida per l'agenzia (email del sito + dominio .it, con diagrammi).
Uso:  python -m tools.pdf_agenzia [percorso_output.pdf]"""
import sys
from datetime import date
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "backend" / "kit_assets" / "fonts"
W, H = 210 * mm, 297 * mm
M = 18 * mm
SCURO, ROSSO, GRIGIO = colors.HexColor("#16161c"), colors.HexColor("#d62828"), colors.HexColor("#5a5a66")
CHIARO, BORDO = colors.HexColor("#f2f2f5"), colors.HexColor("#d9d9e0")
VERDE, ARANCIO = colors.HexColor("#1f8a4c"), colors.HexColor("#c4650a")

pdfmetrics.registerFont(TTFont("Inter", str(F / "Inter-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Inter-Bold", str(F / "Inter-Bold.ttf")))
pdfmetrics.registerFont(TTFont("Mont", str(F / "Montserrat-ExtraBold.ttf")))
pdfmetrics.registerFont(TTFont("Mono", str(F / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("Inter", normal="Inter", bold="Inter-Bold", italic="Inter", boldItalic="Inter-Bold")

body = ParagraphStyle("b", fontName="Inter", fontSize=10.5, leading=15.5, textColor=colors.HexColor("#22222a"))
small = ParagraphStyle("s", parent=body, fontSize=9, leading=13, textColor=GRIGIO)
h1 = ParagraphStyle("h1", fontName="Mont", fontSize=21, leading=25, textColor=SCURO, spaceAfter=4)
h2 = ParagraphStyle("h2", fontName="Inter-Bold", fontSize=13, leading=17, textColor=ROSSO, spaceBefore=8, spaceAfter=4)
cell = ParagraphStyle("c", parent=body, fontSize=9.3, leading=13)
cellb = ParagraphStyle("cb", parent=cell, fontName="Inter-Bold")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "Guida-Agenzia-LMC.pdf"


LOGO_FT = ROOT / "logo" / "fivetech-trasparente.png"      # logo FiveTech ritagliato (sfondo trasparente)
LOGO_LMC = ROOT / "logo" / "logo.png"
VERSIONE = "1.0"


def _logo_ft(c, x, y, h):
    from reportlab.lib.utils import ImageReader
    ir = ImageReader(str(LOGO_FT))
    w0, h0 = ir.getSize()
    c.drawImage(ir, x, y, width=h * w0 / h0, height=h, mask="auto")
    return h * w0 / h0


def deco(c, doc):
    """Pagine interne: intestazione bianca con logo FiveTech, filo rosso, piè di pagina con numerazione (n / totale) in NumberedCanvas."""
    c.saveState()
    _logo_ft(c, M, H - 19 * mm, 11 * mm)
    c.setFillColor(SCURO)
    c.setFont("Mont", 10.5)
    c.drawRightString(W - M, H - 12.5 * mm, "LMC SERVICE")
    c.setFont("Inter", 8.5)
    c.setFillColor(GRIGIO)
    c.drawRightString(W - M, H - 17 * mm, "Guida per l'agenzia: email e dominio")
    c.setFillColor(ROSSO)
    c.rect(0, H - 22 * mm, W, 1.1 * mm, stroke=0, fill=1)
    c.setStrokeColor(BORDO)
    c.line(M, 14 * mm, W - M, 14 * mm)
    c.setFont("Inter", 8)
    c.setFillColor(GRIGIO)
    c.drawString(M, 9 * mm, f"Preparato da FiveTech per La Music Company Service · versione {VERSIONE} · {date.today().strftime('%d/%m/%Y')}")
    c.restoreState()


def copertina(c, doc):
    from reportlab.lib.utils import ImageReader
    c.saveState()
    ir = ImageReader(str(LOGO_LMC))
    ih = W * ir.getSize()[1] / ir.getSize()[0]
    c.drawImage(ir, 0, H - ih, width=W, height=ih)
    c.setFillColor(ROSSO)
    c.rect(0, H - ih - 1.6 * mm, W, 1.6 * mm, stroke=0, fill=1)
    y = H - ih - 24 * mm
    c.setFillColor(ROSSO)
    c.setFont("Inter-Bold", 10)
    c.drawString(M, y, "GUIDA PER L'AGENZIA · COMPLETAMENTO DEL SITO")
    c.setFillColor(SCURO)
    c.setFont("Mont", 30)
    c.drawString(M, y - 14 * mm, "Email del sito")
    c.drawString(M, y - 26 * mm, "e dominio (facoltativo)")
    c.setFillColor(GRIGIO)
    c.setFont("Inter", 12)
    c.drawString(M, y - 37 * mm, "Due completamenti, spiegati in modo semplice")
    # scheda dati
    c.setStrokeColor(BORDO)
    c.setFillColor(CHIARO)
    c.roundRect(M, y - 76 * mm, W - 2 * M, 28 * mm, 3 * mm, stroke=1, fill=1)
    righe = [("Destinatario", "Agenzia pubblicitaria di La Music Company Service"), ("Contenuto", "1. Email del sito · 2. Dominio .it, solo se Pasquale Toppi aderisce"),
             ("Versione", f"{VERSIONE} · {date.today().strftime('%d/%m/%Y')}")]
    for i, (k, v) in enumerate(righe):
        c.setFont("Inter-Bold", 9)
        c.setFillColor(SCURO)
        c.drawString(M + 6 * mm, y - 55 * mm - i * 7 * mm, k)
        c.setFont("Inter", 9)
        c.setFillColor(GRIGIO)
        c.drawString(M + 38 * mm, y - 55 * mm - i * 7 * mm, v)
    # firma
    c.setStrokeColor(BORDO)
    c.line(M, 36 * mm, W - M, 36 * mm)
    c.setFont("Inter", 8.5)
    c.setFillColor(GRIGIO)
    c.drawString(M, 28 * mm, "Preparato da")
    _logo_ft(c, M, 12 * mm, 14 * mm)
    c.setFont("Inter", 8.5)
    c.drawRightString(W - M, 28 * mm, "Documento riservato: non contiene password.")
    c.restoreState()


from reportlab.pdfgen import canvas as _canvas


class NumberedCanvas(_canvas.Canvas):
    """Numera le pagine interne come «Pagina n di N» (la copertina non è numerata)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._salvate = []

    def showPage(self):
        self._salvate.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._salvate)
        for i, st in enumerate(self._salvate):
            self.__dict__.update(st)
            if i > 0:
                self.setFont("Inter", 8)
                self.setFillColor(GRIGIO)
                self.drawRightString(W - M, 9 * mm, f"Pagina {i} di {n - 1}")
            super().showPage()
        super().save()


def box(d, x, y, w, h, titolo, sotto, col, txt=colors.white):
    d.add(Rect(x, y, w, h, rx=7, ry=7, fillColor=col, strokeColor=None))
    d.add(String(x + w / 2, y + h - 17, titolo, fontName="Inter-Bold", fontSize=10.5, fillColor=txt, textAnchor="middle"))
    for i, riga in enumerate(sotto):
        d.add(String(x + w / 2, y + h - 31 - i * 11.5, riga, fontName="Inter", fontSize=8.3, fillColor=txt, textAnchor="middle"))


def freccia(d, x1, y1, x2, y2, col=SCURO, tratteggio=False, et=None):
    ln = Line(x1, y1, x2, y2, strokeColor=col, strokeWidth=2)
    if tratteggio:
        ln.strokeDashArray = [4, 3]
    d.add(ln)
    if abs(y2 - y1) < 1:
        s = 1 if x2 > x1 else -1
        d.add(Polygon([x2, y2, x2 - 8 * s, y2 + 4.5, x2 - 8 * s, y2 - 4.5], fillColor=col, strokeColor=col))
    else:
        s = 1 if y2 > y1 else -1
        d.add(Polygon([x2, y2, x2 - 4.5, y2 - 8 * s, x2 + 4.5, y2 - 8 * s], fillColor=col, strokeColor=col))
    if et:
        d.add(String((x1 + x2) / 2, (y1 + y2) / 2 + 6, et, fontName="Inter-Bold", fontSize=8, fillColor=col, textAnchor="middle"))


def diagramma_flusso():
    d = Drawing(174 * mm, 62 * mm)
    flusso(d, 22 * mm, [("1. Il cliente", ["prenota o chiede", "un preventivo", "sul sito"], colors.HexColor("#3a3a44")),
                        ("2. Il sito", ["prepara", "il messaggio"], SCURO),
                        ("3. Account email", ["lo spedisce", "(es. Gmail)"], ROSSO),
                        ("4. Arriva", ["al cliente: conferma", "a Pasquale: avviso"], VERDE)], h=27 * mm)
    d.add(String(0, 55 * mm, "COME FUNZIONA", fontName="Inter-Bold", fontSize=9.5, fillColor=VERDE))
    d.add(String(0, 9 * mm, "Oggi il passo 3 manca: il sito prepara il messaggio ma non ha un account email da cui spedirlo.", fontName="Inter", fontSize=8.8, fillColor=ARANCIO))
    return d


def tabella(righe, larghezze, intestazione=True):
    dati = [[Paragraph(str(c), cellb if (i == 0 and intestazione) or j == 0 else cell) for j, c in enumerate(r)] for i, r in enumerate(righe)]
    t = Table(dati, colWidths=larghezze, repeatRows=1 if intestazione else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDO), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if intestazione:
        st.append(("BACKGROUND", (0, 0), (-1, 0), CHIARO))
    t.setStyle(TableStyle(st))
    return t


def codice(testo):
    p = Preformatted(testo, ParagraphStyle("m", fontName="Mono", fontSize=8.6, leading=11.5, textColor=colors.HexColor("#1d1d25")))
    t = Table([[p]], colWidths=[174 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CHIARO), ("BOX", (0, 0), (-1, -1), 0.6, BORDO), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def avviso(testo, col=ROSSO, fondo="#fdf0f0"):
    t = Table([[Paragraph(testo, cell)]], colWidths=[174 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fondo)), ("LINEBEFORE", (0, 0), (0, -1), 2.4, col), ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t




def flusso(d, y, voci, larg_tot=174 * mm, h=26 * mm, gap=9 * mm):
    """Riga di riquadri collegati da frecce. voci = [(titolo, [righe], colore)]"""
    n = len(voci)
    w = (larg_tot - gap * (n - 1)) / n
    for i, (t, r, col) in enumerate(voci):
        x = i * (w + gap)
        box(d, x, y, w, h, t, r, col)
        if i < n - 1:
            freccia(d, x + w, y + h / 2, x + w + gap, y + h / 2)


def diagramma_marcia():
    d = Drawing(174 * mm, 50 * mm)
    flusso(d, 14 * mm, [("PASSO 1 · email", ["si può fare", "subito"], VERDE), ("PASSO 2 · dominio", ["facoltativo:", "lo decide Pasquale"], ROSSO)], larg_tot=120 * mm, h=26 * mm, gap=14 * mm)
    return d


def ridim(d, f):
    d.scale(f, f)
    d.width *= f
    d.height *= f
    return d


def casella(testo):
    t = Table([["", Paragraph(testo, cell)]], colWidths=[7 * mm, 160 * mm], rowHeights=[8 * mm])
    t.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 1.2, SCURO), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (1, 0), (1, 0), 8)]))
    return t


# ================================================================ contenuto
sub = ParagraphStyle("sub", parent=body, fontSize=12, textColor=GRIGIO)
el = [Spacer(1, 1), NextPageTemplate("p"), PageBreak()]
el += [Paragraph("In breve", h1), Paragraph("Il sito è online e funziona. Mancano due cose.", sub), Spacer(1, 5 * mm),
       tabella([["Già pronto", "Da completare"],
                ["Vetrina con video e galleria<br/>Prenotazioni e preventivi<br/>Area riservata per Pasquale e i collaboratori<br/>Copia di sicurezza ogni notte",
                 "<b>1. Email del sito</b>: oggi non parte nessuna email, né ai clienti né a Pasquale<br/><b>2. Dominio .it</b>: un indirizzo più professionale (facoltativo)"]],
               [87 * mm, 87 * mm]),
       Spacer(1, 5 * mm), diagramma_marcia(),
       Paragraph("Cosa chiediamo all'agenzia", h2),
       tabella([["Passo", "Cosa serve", "Chi decide"],
                ["1. Email", "Un account email da cui il sito possa spedire. La soluzione più semplice è usare quello di Pasquale (anche Gmail).", "Pasquale: basta il suo consenso"],
                ["2. Dominio", "Un nome per il sito, per esempio il nome dell'attività con «.it». Costa poco, una volta l'anno.", "Pasquale: è un'idea da valutare insieme"]],
               [26 * mm, 100 * mm, 48 * mm]),
       Spacer(1, 5 * mm),
       Paragraph("La decisione di Pasquale Toppi sul dominio", h2),
       casella("<b>Aderisco</b>: procediamo con il dominio .it, intestato a me."), Spacer(1, 1.5 * mm),
       casella("<b>Non ora</b>: per il momento il sito resta com'è e facciamo solo le email."), Spacer(1, 5 * mm),
       Paragraph("Firma ________________________________      Data ____________________", small),
       PageBreak()]
el += [Paragraph("1. Email del sito", h1), Paragraph("Si può fare subito · circa 15 minuti", ParagraphStyle("f", parent=body, textColor=VERDE)), Spacer(1, 3 * mm),
       Paragraph("Quando un cliente prenota, il sito deve poter <b>spedire un'email</b>, come un ufficio che ha bisogno di una casella di posta per scrivere. Oggi quella casella non è collegata, quindi nessuna email parte.", body), Spacer(1, 4 * mm),
       diagramma_flusso(), Spacer(1, 2 * mm),
       Paragraph("Quali email partono", h2),
       tabella([["A chi", "Quando"],
                ["Cliente", "Conferma di prenotazione o di preventivo, promemoria il giorno prima, richiesta di recensione dopo l'evento"],
                ["Pasquale", "Avviso a ogni nuova richiesta, annullamento o recensione"]],
               [30 * mm, 144 * mm]),
       Spacer(1, 4 * mm),
       Paragraph("Cosa serve all'agenzia", h2),
       tabella([["#", "Cosa fare", "Chi"],
                ["1", "Scegliere l'account email da usare. Il più semplice: <b>quello di Pasquale</b> (anche Gmail, gratuito e sufficiente)", "Agenzia con Pasquale"],
                ["2", "Su quell'account attivare la «verifica in due passaggi» e creare una <b>«password per le app»</b>, dandole il nome «Sito LMC»", "Agenzia con Pasquale"],
                ["3", "Comunicare a FiveTech <b>account e password per le app</b> di persona o a voce, <b>mai per email o chat</b>", "Agenzia"],
                ["4", "FiveTech li inserisce nel sito e fa una prenotazione di prova: devono arrivare la conferma e l'avviso", "FiveTech"]],
               [8 * mm, 116 * mm, 50 * mm]),
       Spacer(1, 4 * mm),
       avviso("<b>Sicurezza.</b> La «password per le app» è diversa da quella normale: se serve, si cancella in qualsiasi momento senza toccare l'account di Pasquale.", ARANCIO, "#fff4e8"),
       PageBreak()]
el += [Paragraph("2. Dominio .it", h1), Paragraph("Facoltativo · da decidere con Pasquale Toppi", ParagraphStyle("f", parent=body, textColor=ROSSO)), Spacer(1, 3 * mm),
       Paragraph("Oggi il sito si apre da un indirizzo di servizio gratuito: funziona, ma è lungo e poco professionale. Un dominio <b>.it</b> è un indirizzo breve col nome dell'attività, facile da dettare, da stampare sui biglietti e sui QR.", body), Spacer(1, 4 * mm),
       tabella([["Perché conviene", "Cosa comporta"],
                ["Più fiducia da parte dei clienti<br/>Indirizzo facile da ricordare e da dettare<br/>Email professionali con il nome dell'attività<br/>Resta di Pasquale anche se cambia agenzia",
                 "Costo annuale basso, da chiedere al fornitore<br/>Il dominio è <b>intestato a Pasquale</b>, non all'agenzia<br/>Servono i suoi dati di titolare, che inserisce lui<br/>Il vecchio indirizzo continua a funzionare"]],
               [87 * mm, 87 * mm]),
       Spacer(1, 5 * mm),
       Paragraph("Come si procede, se Pasquale aderisce", h2),
       tabella([["#", "Cosa", "Chi"],
                ["1", "Pasquale sceglie il nome e registra il dominio a suo nome", "Pasquale"],
                ["2", "L'agenzia collega il dominio al sito, seguendo le indicazioni di FiveTech", "Agenzia + FiveTech"],
                ["3", "FiveTech attiva il lucchetto di sicurezza (HTTPS) e controlla che tutto funzioni", "FiveTech"],
                ["4", "Si aggiornano QR, social e biglietti con il nuovo indirizzo; se serve, si crea anche l'email col dominio", "Insieme"]],
               [8 * mm, 116 * mm, 50 * mm]),
       Spacer(1, 4 * mm),
       avviso("<b>Nessuna fretta.</b> Il sito funziona già così com'è. Il dominio si può aggiungere in qualsiasi momento, e le credenziali del dominio restano sempre a Pasquale.", VERDE, "#eef8f1"),
       Spacer(1, 6 * mm), Paragraph("Checklist", h2),
       casella("Email del sito attive (prenotazione di prova ricevuta)"), Spacer(1, 1 * mm),
       casella("Pasquale ha deciso sul dominio (pagina «In breve»)"), Spacer(1, 1 * mm),
       casella("Se sì: dominio registrato a nome di Pasquale e sito collegato"), Spacer(1, 4 * mm),
       Paragraph("Per dubbi scrivere a FiveTech, <b>senza mai includere password</b>.", small)]

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUT), pagesize=(W, H), leftMargin=M, rightMargin=M, topMargin=28 * mm, bottomMargin=20 * mm, title="Guida per l'agenzia: email del sito e dominio", author="FiveTech", subject="Guida agenzia")
fr = Frame(M, 20 * mm, W - 2 * M, H - 48 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="cover", frames=[Frame(M, 20 * mm, W - 2 * M, H - 40 * mm, id="c")], onPage=copertina), PageTemplate(id="p", frames=[fr], onPage=deco)])
doc.build(el, canvasmaker=NumberedCanvas)
print(OUT)
