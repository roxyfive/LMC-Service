"""Sistema grafico del libretto illustrativo LMC (ReportLab): colori, caratteri, componenti, diagrammi.
Usato da tools/pdf_libretto.py."""
import re
import tempfile
from datetime import date
from pathlib import Path

from PIL import Image as PI
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as _canvas
from reportlab.platypus import Flowable, Image, KeepTogether, Paragraph, Preformatted, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "backend" / "kit_assets" / "fonts"
W, H = 210 * mm, 297 * mm
M = 18 * mm
CW = W - 2 * M                                   # larghezza utile
VERSIONE = "1.0"

NERO, ANTRA, ROSSO, ROSSO2 = colors.HexColor("#0f0f14"), colors.HexColor("#16161c"), colors.HexColor("#e11d14"), colors.HexColor("#ff5a52")
GRIGIO, CHIARO, BORDO, TESTO = colors.HexColor("#5a5a66"), colors.HexColor("#f4f4f7"), colors.HexColor("#dcdce3"), colors.HexColor("#22222a")
TEAL, AMBRA, BLU, VERDE = colors.HexColor("#14917a"), colors.HexColor("#d98a00"), colors.HexColor("#3b6fd8"), colors.HexColor("#1f8a4c")
RUOLO = {"ADMIN": ROSSO, "COLLABORATORE": AMBRA, "CLIENTE": TEAL, "TECNICO": BLU}
LOGO_FT = ROOT / "logo" / "fivetech-trasparente.png"
LOGO_LMC = ROOT / "logo" / "logo.png"

for nome, f in (("Inter", "Inter-Regular.ttf"), ("Inter-Bold", "Inter-Bold.ttf"), ("Mont", "Montserrat-ExtraBold.ttf"), ("Grot", "SpaceGrotesk-SemiBold.ttf"), ("Mono", "DejaVuSansMono.ttf")):
    pdfmetrics.registerFont(TTFont(nome, str(F / f)))
pdfmetrics.registerFontFamily("Inter", normal="Inter", bold="Inter-Bold", italic="Inter", boldItalic="Inter-Bold")

body = ParagraphStyle("body", fontName="Inter", fontSize=10, leading=15, textColor=TESTO)
small = ParagraphStyle("small", parent=body, fontSize=8.6, leading=12.4, textColor=GRIGIO)
lead = ParagraphStyle("lead", parent=body, fontSize=12, leading=17.5, textColor=GRIGIO)
h1 = ParagraphStyle("h1", fontName="Mont", fontSize=21, leading=25, textColor=ANTRA, spaceAfter=2)
h2 = ParagraphStyle("h2", fontName="Inter-Bold", fontSize=12.5, leading=16, textColor=ROSSO, spaceBefore=9, spaceAfter=4)
h3 = ParagraphStyle("h3", fontName="Inter-Bold", fontSize=10.5, leading=14, textColor=ANTRA, spaceBefore=5, spaceAfter=2)
cell = ParagraphStyle("cell", parent=body, fontSize=8.9, leading=12.6)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Inter-Bold")
cellh = ParagraphStyle("cellh", parent=cell, fontName="Inter-Bold", textColor=colors.white)
cap = ParagraphStyle("cap", parent=small, fontSize=7.8, leading=10.5)

_JPG = {}


def jpg(path, maxw=1500):
    """Riduce lo screenshot a JPEG leggero (PDF di dimensioni ragionevoli)."""
    path = Path(path)
    if path in _JPG:
        return _JPG[path]
    im = PI.open(path).convert("RGB")
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), PI.LANCZOS)
    out = Path(tempfile.mkdtemp(prefix="lmc_lib_")) / (path.stem + ".jpg")
    im.save(out, quality=84, optimize=True)
    _JPG[path] = out
    return out


def logo_ft(c, x, y, h):
    ir = ImageReader(str(LOGO_FT))
    w0, h0 = ir.getSize()
    c.drawImage(ir, x, y, width=h * w0 / h0, height=h, mask="auto")
    return h * w0 / h0


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ componenti
class Chips(Flowable):
    """Etichette dei ruoli (ADMIN, COLLABORATORE, CLIENTE...) colorate."""

    def __init__(self, ruoli):
        super().__init__()
        self.ruoli = ruoli
        self.width, self.height = CW, 7 * mm

    def wrap(self, aw, ah):
        return aw, 7 * mm

    def draw(self):
        c = self.canv
        x = 0
        for r in self.ruoli:
            col = RUOLO.get(r, GRIGIO)
            w = pdfmetrics.stringWidth(r, "Inter-Bold", 7.2) + 9 * mm / 2.2
            c.setFillColor(col)
            c.roundRect(x, 0.8 * mm, w, 5 * mm, 2.5 * mm, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont("Inter-Bold", 7.2)
            c.drawCentredString(x + w / 2, 2.55 * mm, r)
            x += w + 2 * mm


def titolo(testo, ruoli=None, key=None, level=1):
    """Titolo di sezione con chip dei ruoli, filo colore e voce dell'indice cliccabile."""
    out = []
    if ruoli:
        out.append(Chips(ruoli))
    p = Paragraph(esc(testo), h1)
    p._toc = (level, testo, key or re.sub(r"\W+", "_", testo.lower()))
    out.append(p)
    col = RUOLO.get(ruoli[0], ROSSO) if ruoli else ROSSO
    out.append(Table([[""]], colWidths=[26 * mm], rowHeights=[1.6 * mm], style=[("BACKGROUND", (0, 0), (-1, -1), col)], hAlign="LEFT"))
    out.append(Spacer(1, 3 * mm))
    return out


def numero(n, col=ROSSO, d=5.2 * mm):
    dr = Drawing(d, d)
    dr.add(Circle(d / 2, d / 2, d / 2, fillColor=col, strokeColor=None))
    dr.add(String(d / 2, d / 2 - 2.4, str(n), fontName="Grot", fontSize=8.8, fillColor=colors.white, textAnchor="middle"))
    return dr


def passi(lista, col=ROSSO):
    rows = [[numero(i, col), Paragraph(t, body)] for i, t in enumerate(lista, 1)]
    t = Table(rows, colWidths=[8 * mm, CW - 8 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
    return t


NOTA = {"consiglio": (VERDE, "#eef8f2", "Consiglio"), "attenzione": (AMBRA, "#fff6e6", "Attenzione"), "sicurezza": (ROSSO, "#fdf0f0", "Sicurezza"),
        "info": (BLU, "#eef3fd", "Da sapere"), "regola": (ANTRA, "#f1f1f4", "Regola d'oro")}


def nota(testo, tipo="info", w=CW):
    col, bg, et = NOTA[tipo]
    t = Table([[Paragraph(f"<font name='Inter-Bold' color='{col.hexval().replace('0x', '#')}'>{et}.</font> {testo}", cell)]], colWidths=[w])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)), ("LINEBEFORE", (0, 0), (0, -1), 2.6, col), ("LEFTPADDING", (0, 0), (-1, -1), 9),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5)]))
    return t


def tabella(righe, larg, zebra=True, testa=True, size=None):
    st = cell if not size else ParagraphStyle("t", parent=cell, fontSize=size, leading=size + 3.6)
    dati = []
    for i, r in enumerate(righe):
        dati.append([c if isinstance(c, Flowable) else Paragraph(str(c), cellh if (i == 0 and testa) else (cellb if j == 0 else st)) for j, c in enumerate(r)])
    t = Table(dati, colWidths=larg, repeatRows=1 if testa else 0)
    s = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDO), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
         ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if testa:
        s.append(("BACKGROUND", (0, 0), (-1, 0), ANTRA))
    if zebra:
        for i in range(1 if testa else 0, len(righe)):
            if (i % 2) == 0:
                s.append(("BACKGROUND", (0, i), (-1, i), CHIARO))
    t.setStyle(TableStyle(s))
    return t


def codice(testo):
    p = Preformatted(testo, ParagraphStyle("m", fontName="Mono", fontSize=8.4, leading=11.4, textColor=colors.HexColor("#e8e8ee")))
    t = Table([[p]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ANTRA), ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def legenda(voci, w, col=ROSSO, start=1):
    rows = [[numero(i, col, 5 * mm), Paragraph(t, cell)] for i, t in enumerate(voci, start)]
    t = Table(rows, colWidths=[7 * mm, w - 7 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 2.4), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4)]))
    return t


def img(shots, stem, dev, w):
    p = Path(shots) / f"{stem}-{dev}.png"
    if not p.exists():
        return None
    iw, ih = PI.open(p).size
    return Image(str(jpg(p, 1500 if dev == "desktop" else 800)), width=w, height=w * ih / iw)


def cornice(im):
    t = Table([[im]], colWidths=[im.drawWidth + 1.6 * mm])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, BORDO), ("BACKGROUND", (0, 0), (-1, -1), colors.white), ("LEFTPADDING", (0, 0), (-1, -1), 0.8 * mm),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0.8 * mm), ("TOPPADDING", (0, 0), (-1, -1), 0.8 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.8 * mm)]))
    return t


def schermata(shots, stem, leg=None, col=ROSSO, didascalia=None, wd=None):
    """Screenshot desktop a tutta larghezza con la legenda numerata sotto, su due colonne (i numeri corrispondono ai cerchi rossi)."""
    im = img(shots, stem, "desktop", wd or 150 * mm)
    if im is None:
        return Spacer(1, 1)
    out = [cornice(im)]
    if didascalia:
        out.append(Paragraph(didascalia, cap))
    if leg:
        out.append(Spacer(1, 2 * mm))
        k = (len(leg) + 1) // 2
        a_, b_ = leg[:k], leg[k:]
        wc = CW / 2 - 4 * mm
        celle = [legenda(a_, wc, col, 1)] + ([legenda(b_, wc, col, k + 1)] if b_ else [""])
        t = Table([celle], colWidths=[CW / 2, CW / 2])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm)]))
        out.append(t)
    return KeepTogether(out)


def coppia(shots, stem, didascalia=None, wd=118 * mm, wm=38 * mm):
    """Sito: versione computer (grande) + telefono (stretta) affiancate."""
    d, m = img(shots, stem, "desktop", wd), img(shots, stem, "mobile", wm)
    celle = [cornice(x) for x in (d, m) if x is not None]
    if not celle:
        return Spacer(1, 1)
    t = Table([celle], colWidths=[wd + 2 * mm, wm + 4 * mm][:len(celle)])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm)]))
    out = [t]
    if didascalia:
        out.append(Paragraph(didascalia, cap))
    return KeepTogether(out)


# ------------------------------------------------------------------ diagrammi
def _box(d, x, y, w, h, tit, righe=(), col=ANTRA, txt=colors.white, r=6, fs=9.5):
    d.add(Rect(x, y, w, h, rx=r, ry=r, fillColor=col, strokeColor=None))
    d.add(String(x + w / 2, y + h - 5 * mm + 1, tit, fontName="Inter-Bold", fontSize=fs, fillColor=txt, textAnchor="middle"))
    for i, t in enumerate(righe):
        d.add(String(x + w / 2, y + h - 5 * mm - 3.6 * mm * (i + 1) + 1, t, fontName="Inter", fontSize=7.6, fillColor=txt, textAnchor="middle"))


def _arrow(d, x1, y1, x2, y2, col=ANTRA, w=1.8, dash=False, label=None):
    ln = Line(x1, y1, x2, y2, strokeColor=col, strokeWidth=w)
    if dash:
        ln.strokeDashArray = [4, 3]
    d.add(ln)
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    L = 7
    d.add(Polygon([x2, y2, x2 - L * math.cos(a - 0.45), y2 - L * math.sin(a - 0.45), x2 - L * math.cos(a + 0.45), y2 - L * math.sin(a + 0.45)], fillColor=col, strokeColor=col))
    if label:
        d.add(String((x1 + x2) / 2, (y1 + y2) / 2 + 2.2 * mm, label, fontName="Inter-Bold", fontSize=7.2, fillColor=col, textAnchor="middle"))


def riga(d, y, voci, h=24 * mm, gap=8 * mm, x0=0, tot=CW, fs=9.5):
    n = len(voci)
    w = (tot - gap * (n - 1)) / n
    for i, v in enumerate(voci):
        tit, righe, col = v
        x = x0 + i * (w + gap)
        _box(d, x, y, w, h, tit, righe, col, fs=fs)
        if i < n - 1:
            _arrow(d, x + w + 0.8 * mm, y + h / 2, x + w + gap - 0.8 * mm, y + h / 2)


def ridim(d, f):
    d.scale(f, f)
    d.width *= f
    d.height *= f
    return d


# ------------------------------------------------------------------ pagina: decorazioni
def make_deco(parte, col):
    def deco(c, doc):
        c.saveState()
        logo_ft(c, M, H - 19 * mm, 11 * mm)
        c.setFillColor(ANTRA)
        c.setFont("Mont", 10)
        c.drawRightString(W - M, H - 12 * mm, "LIBRETTO LMC SERVICE")
        c.setFont("Inter-Bold", 8)
        c.setFillColor(col)
        c.drawRightString(W - M, H - 17 * mm, parte.upper())
        c.setFillColor(col)
        c.rect(0, H - 22 * mm, W, 1.3 * mm, stroke=0, fill=1)
        c.setStrokeColor(BORDO)
        c.line(M, 14 * mm, W - M, 14 * mm)
        c.setFont("Inter", 7.8)
        c.setFillColor(GRIGIO)
        c.drawString(M, 9 * mm, f"La Music Company Service · Libretto illustrativo · versione {VERSIONE} · {date.today().strftime('%d/%m/%Y')} · preparato da FiveTech")
        c.restoreState()
    return deco


class NumberedCanvas(_canvas.Canvas):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._s = []

    def showPage(self):
        self._s.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._s)
        for i, st in enumerate(self._s):
            self.__dict__.update(st)
            if i > 0 and not getattr(self, "_nonum", False):
                self.setFont("Inter-Bold", 8)
                self.setFillColor(GRIGIO)
                self.drawRightString(W - M, 9 * mm, f"{i + 1} / {n}")
            super().showPage()
        super().save()


class Divider(Flowable):
    """Pagina di apertura di una parte: tutta scura a pieno foglio, numero grande a contorno, titolo e indice della parte."""

    def __init__(self, num, titolo_, sotto, voci, col):
        super().__init__()
        self.num, self.t, self.s, self.voci, self.col = num, titolo_, sotto, voci, col
        self._toc = (0, f"Parte {num} · {titolo_}", f"parte_{num}")

    def wrap(self, aw, ah):
        self.aw, self.ah = aw, ah
        return aw, ah - 1

    def draw(self):
        c = self.canv
        c.saveState()
        c.translate(-M, -20 * mm)
        c.setFillColor(NERO)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        ir = ImageReader(str(LOGO_LMC))
        ih = W * ir.getSize()[1] / ir.getSize()[0]
        c.saveState()
        c.setFillAlpha(0.35)
        c.drawImage(ir, 0, -14 * mm, width=W, height=ih)
        c.restoreState()
        c.setFillColor(self.col)
        c.rect(0, H - 8 * mm, W, 8 * mm, stroke=0, fill=1)
        c.setFont("Inter-Bold", 11)
        c.setFillColor(self.col)
        c.drawString(M, H - 40 * mm, f"PARTE {self.num}")
        # numero gigante a contorno
        c.saveState()
        c.setStrokeColor(self.col)
        c.setLineWidth(2.2)
        c.setFillColor(NERO)
        t = c.beginText(M - 4 * mm, H - 112 * mm)
        t.setFont("Mont", 150)
        t.setTextRenderMode(1)
        t.textOut(str(self.num))
        c.drawText(t)
        c.restoreState()
        c.setFillColor(colors.white)
        c.setFont("Mont", 30)
        for i, riga_ in enumerate(self.t.split("\n")):
            c.drawString(M, H - 136 * mm - i * 12 * mm, riga_)
        c.setFont("Inter", 12.5)
        c.setFillColor(colors.HexColor("#c8c8d2"))
        y = H - 136 * mm - 12 * mm * len(self.t.split("\n")) - 4 * mm
        for riga_ in self.s.split("\n"):
            c.drawString(M, y, riga_)
            y -= 6.5 * mm
        y -= 6 * mm
        c.setFont("Inter-Bold", 9)
        c.setFillColor(self.col)
        c.drawString(M, y, "IN QUESTA PARTE")
        y -= 6.5 * mm
        c.setFont("Inter", 10.5)
        c.setFillColor(colors.white)
        for v in self.voci:
            c.drawString(M + 5 * mm, y, v)
            c.setFillColor(self.col)
            c.circle(M + 1.2 * mm, y + 1.3 * mm, 1.1 * mm, stroke=0, fill=1)
            c.setFillColor(colors.white)
            y -= 5.6 * mm
        c.restoreState()
