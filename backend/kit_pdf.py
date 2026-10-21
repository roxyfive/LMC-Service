"""Generatore delle guide PDF del kit (ReportLab).

Ogni pagina ha l'intestazione scura col logo FiveTech e il piè di pagina con data, versione e numero di pagina.
L'indice in seconda pagina è cliccabile (ogni voce porta alla sezione).
"""
import re
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph, Preformatted, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from . import kit_testi

BASE = Path(__file__).resolve().parent
FONTS = BASE / "kit_assets" / "fonts"
LOGO = BASE.parent / "logo" / "fivetech.png"
W, H = 210 * mm, 297 * mm
MARGIN = 18 * mm
TOP = 30 * mm
BOTTOM = 20 * mm

SCURO = colors.HexColor("#16161c")
SCURO2 = colors.HexColor("#1c1c22")
ROSSO = colors.HexColor("#d62828")
GRIGIO = colors.HexColor("#5a5a66")
CHIARO = colors.HexColor("#f2f2f5")
BORDO = colors.HexColor("#d9d9e0")


def _fonts():
    if "Inter" in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont("Inter", str(FONTS / "Inter-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Inter-Bold", str(FONTS / "Inter-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Mont", str(FONTS / "Montserrat-ExtraBold.ttf")))
    pdfmetrics.registerFont(TTFont("Grotesk", str(FONTS / "SpaceGrotesk-SemiBold.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", str(FONTS / "DejaVuSansMono.ttf")))
    pdfmetrics.registerFontFamily("Inter", normal="Inter", bold="Inter-Bold", italic="Inter", boldItalic="Inter-Bold")


def _styles():
    s = {}
    s["body"] = ParagraphStyle("body", fontName="Inter", fontSize=10, leading=15, textColor=colors.HexColor("#22222a"), alignment=TA_LEFT)
    s["small"] = ParagraphStyle("small", parent=s["body"], fontSize=8.5, leading=12, textColor=GRIGIO)
    s["h1"] = ParagraphStyle("h1", fontName="Mont", fontSize=19, leading=23, textColor=SCURO, spaceBefore=0, spaceAfter=4)
    s["h2"] = ParagraphStyle("h2", fontName="Inter-Bold", fontSize=11.5, leading=15, textColor=ROSSO, spaceBefore=8, spaceAfter=4)
    s["step"] = ParagraphStyle("step", parent=s["body"], leftIndent=0)
    s["note"] = ParagraphStyle("note", parent=s["body"], fontSize=9.5, leading=14, textColor=colors.HexColor("#33333b"))
    s["cover_t"] = ParagraphStyle("cover_t", fontName="Mont", fontSize=34, leading=38, textColor=SCURO)
    s["cover_s"] = ParagraphStyle("cover_s", fontName="Inter", fontSize=13, leading=19, textColor=GRIGIO)
    s["toc1"] = ParagraphStyle("toc1", fontName="Inter-Bold", fontSize=11, leading=22, textColor=SCURO, leftIndent=0, rightIndent=20)
    s["cell"] = ParagraphStyle("cell", parent=s["body"], fontSize=9, leading=13)
    s["cellb"] = ParagraphStyle("cellb", parent=s["cell"], fontName="Inter-Bold")
    s["cap"] = ParagraphStyle("cap", parent=s["small"], fontSize=8, leading=11)
    return s


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Doc(BaseDocTemplate):
    def __init__(self, path, titolo, sottotitolo, data=None):
        _fonts()
        self.titolo, self.sottotitolo = titolo, sottotitolo
        self.data = (data or date.today()).strftime("%d/%m/%Y")
        super().__init__(str(path), pagesize=(W, H), leftMargin=MARGIN, rightMargin=MARGIN, topMargin=TOP, bottomMargin=BOTTOM,
                         title=titolo, author="FiveTech", subject=sottotitolo, creator="LMC Service kit di consegna")
        fr = Frame(MARGIN, BOTTOM, W - 2 * MARGIN, H - TOP - BOTTOM, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="p", frames=[fr], onPage=self._decor)])
        self._logo = ImageReader(str(LOGO))

    def _decor(self, c, doc):
        c.saveState()
        # intestazione scura con logo FiveTech
        c.setFillColor(SCURO)
        c.rect(0, H - 22 * mm, W, 22 * mm, stroke=0, fill=1)
        c.setFillColor(ROSSO)
        c.rect(0, H - 22.8 * mm, W, 0.8 * mm, stroke=0, fill=1)
        lw = 17 * mm * 700 / 382 * 0.9
        c.drawImage(self._logo, MARGIN, H - 20 * mm, width=lw, height=lw * 382 / 700, mask="auto")
        c.setFillColor(colors.white)
        c.setFont("Mont", 9.5)
        c.drawRightString(W - MARGIN, H - 10.5 * mm, "LMC SERVICE")
        c.setFont("Inter", 8)
        c.setFillColor(colors.HexColor("#c5c5cf"))
        c.drawRightString(W - MARGIN, H - 15.5 * mm, self.titolo)
        # piè di pagina
        c.setStrokeColor(BORDO)
        c.setLineWidth(0.5)
        c.line(MARGIN, 14 * mm, W - MARGIN, 14 * mm)
        c.setFont("Inter", 8)
        c.setFillColor(GRIGIO)
        c.drawString(MARGIN, 9 * mm, f"{self.titolo}  ·  versione {kit_testi.VERSIONE}  ·  {self.data}")
        c.drawRightString(W - MARGIN, 9 * mm, f"Pagina {doc.page}")
        c.restoreState()

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name == "h1" and getattr(fl, "_toc", None):
            key = fl._toc
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(re.sub(r"<[^>]+>", "", fl.text), key, 0, 0)
            self.notify("TOCEntry", (0, re.sub(r"<[^>]+>", "", fl.text), self.page, key))


_CACHE = {}


def _prep(f):
    """Riduce lo screenshot a JPEG (PDF leggero): massimo 1500 px di larghezza."""
    f = Path(f)
    if f in _CACHE:
        return _CACHE[f]
    import tempfile
    from PIL import Image as PI
    im = PI.open(f).convert("RGB")
    if im.width > 1500:
        im = im.resize((1500, round(im.height * 1500 / im.width)), PI.LANCZOS)
    out = Path(tempfile.mkdtemp(prefix="lmc_pdf_")) / (f.stem + ".jpg")
    im.save(out, quality=84, optimize=True)
    _CACHE[f] = out
    return out


def _shot(shots, base, st, maxw, maxh):
    """Screenshot desktop (grande) + mobile (stretto) affiancati, se presenti."""
    d = Path(shots) / f"{base}.png"
    m = Path(shots) / f"{base.replace('desktop', 'mobile')}.png"
    cells, widths = [], []
    if d.exists():
        from PIL import Image as PI
        iw, ih = PI.open(d).size
        w = maxw * 0.68 if m.exists() else maxw
        h = w * ih / iw
        if h > maxh:
            h = maxh
            w = h * iw / ih
        cells.append(Image(str(_prep(d)), width=w, height=h))
        widths.append(w + 4 * mm)
    if m.exists():
        from PIL import Image as PI
        iw, ih = PI.open(m).size
        w = maxw * 0.27
        h = w * ih / iw
        if h > maxh:
            h = maxh
            w = h * iw / ih
        cells.append(Image(str(_prep(m)), width=w, height=h))
        widths.append(w)
    if not cells:
        return None
    t = Table([cells], colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("BOX", (0, 0), (0, 0), 0.6, BORDO)] + ([("BOX", (1, 0), (1, 0), 0.6, BORDO)] if len(cells) > 1 else [])))
    return t


def _schema(text, avail):
    lines = text.rstrip("\n").split("\n")
    longest = max(len(x) for x in lines)
    size = min(8, (avail - 8 * mm) / (longest * 0.602))
    size = max(size, 4.8)
    pre = Preformatted(text.rstrip("\n"), ParagraphStyle("pre", fontName="Mono", fontSize=size, leading=size * 1.25, textColor=colors.HexColor("#1d1d25")))
    t = Table([[pre]], colWidths=[avail])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CHIARO), ("BOX", (0, 0), (-1, -1), 0.6, BORDO), ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                           ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm)]))
    return t


def _callout(text, st, avail, titolo="Da sapere"):
    p = Paragraph(f"<b>{titolo}.</b> {esc(text)}", st["note"])
    t = Table([[p]], colWidths=[avail])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf0f0")), ("LINEBEFORE", (0, 0), (0, -1), 2.2, ROSSO),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                           ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm)]))
    return t


def _steps(passi, st, avail):
    rows = []
    for i, p in enumerate(passi, 1):
        rows.append([Paragraph(f"<font name='Grotesk' color='#d62828' size='11'>{i}</font>", st["step"]), Paragraph(esc(p), st["step"])])
    t = Table(rows, colWidths=[8 * mm, avail - 8 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6)]))
    return t


def _kv(rows, st, avail, w1=38 * mm):
    data = [[Paragraph(esc(a), st["cellb"]), Paragraph(esc(b), st["cell"])] for a, b in rows]
    t = Table(data, colWidths=[w1, avail - w1], repeatRows=0)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDO), ("TOPPADDING", (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return t


RUOLI_TAB = [("Dashboard", "Sì", "Sì (senza incassi)"), ("Agenda / Calendario", "Sì", "Sì"), ("Richieste e riepilogo WhatsApp", "Sì", "Sì"),
             ("Preventivi", "Sì", "No"), ("Fatture", "Sì", "No"), ("Acconti e incassi", "Sì", "No"), ("Galleria: carica foto", "Sì", "Sì (restano nascoste)"),
             ("Galleria: pubblica / elimina", "Sì", "No"), ("Materiale e check-list", "Sì", "Sì"), ("Assistente", "Sì", "Sì"), ("Recensioni", "Sì", "No"),
             ("Tariffe", "Sì", "No"), ("Statistiche", "Sì", "No"), ("Impostazioni, WhatsApp, Backup", "Sì", "No"), ("Utenti e permessi, Registro attività", "Sì", "No")]


def _ruoli(st, avail):
    data = [[Paragraph("Funzione", st["cellb"]), Paragraph("ADMIN", st["cellb"]), Paragraph("COLLABORATORE", st["cellb"])]]
    for a, b, c in RUOLI_TAB:
        data.append([Paragraph(a, st["cell"]), Paragraph(b, st["cell"]), Paragraph(c, st["cell"])])
    t = Table(data, colWidths=[avail * 0.5, avail * 0.2, avail * 0.3], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), CHIARO), ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDO), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def _qr_block(qrs, st, avail):
    """qrs = [(titolo, url, percorso_png)] affiancati con didascalia."""
    side = 50 * mm
    cells = []
    for tit, url, png in qrs:
        cells.append([Image(str(png), width=side, height=side), Spacer(1, 2 * mm), Paragraph(f"<b>{esc(tit)}</b>", ParagraphStyle("qt", parent=st["body"], alignment=1, fontSize=10)),
                      Paragraph(esc(url), ParagraphStyle("qu", parent=st["small"], alignment=1))])
    t = Table([cells], colWidths=[avail / len(cells)] * len(cells))
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def build(path, titolo, sottotitolo, intro_cover, sezioni, shots, qrs, extra=None, data=None):
    """Costruisce un PDF. extra = lista di ('ruoli'|'specifiche', titolo) da aggiungere in fondo come sezioni."""
    st = _styles()
    doc = Doc(path, titolo, sottotitolo, data)
    avail = W - 2 * MARGIN
    el = []
    # ---- copertina
    el += [Spacer(1, 18 * mm), Paragraph("GUIDA", ParagraphStyle("k", fontName="Inter-Bold", fontSize=11, textColor=ROSSO, leading=14)),
           Paragraph(esc(titolo.replace("Guida ", "")).upper() if False else esc(titolo), st["cover_t"]), Spacer(1, 4 * mm),
           Paragraph(esc(sottotitolo), st["cover_s"]), Spacer(1, 8 * mm), Paragraph(esc(intro_cover), st["body"]), Spacer(1, 10 * mm)]
    el.append(_qr_block(qrs, st, avail))
    el += [Spacer(1, 6 * mm), Paragraph("Inquadra il QR con la fotocamera del telefono. I due QR (in alta risoluzione, pronti da stampare) sono anche nella cartella <b>qr/</b> del kit.", st["small"]),
           Spacer(1, 10 * mm),
           Paragraph(f"Versione {kit_testi.VERSIONE} · {doc.data} · realizzata da FiveTech per La Music Company Service", st["small"]), PageBreak()]
    # ---- indice cliccabile
    toc = TableOfContents()
    toc.levelStyles = [st["toc1"]]
    toc.dotsMinLevel = 0
    el += [Paragraph("Indice", ParagraphStyle("it", parent=st["h1"])), Paragraph("Tocca una voce per saltare alla sezione.", st["small"]), Spacer(1, 4 * mm), toc, PageBreak()]
    # ---- sezioni
    voci = list(sezioni)
    if extra:
        voci += [dict(id=k, titolo=t, speciale=k) for k, t in extra]
    for i, s in enumerate(voci):
        h = Paragraph(esc(s["titolo"]), st["h1"])
        h._toc = "sec_" + s["id"]
        blocco = [h, Table([[""]], colWidths=[24 * mm], rowHeights=[1.6 * mm], style=[("BACKGROUND", (0, 0), (-1, -1), ROSSO)], hAlign="LEFT"), Spacer(1, 3 * mm)]
        if s.get("speciale") == "ruoli":
            blocco += [Paragraph("Chi può fare cosa. L'ADMIN è il titolare; il COLLABORATORE vede solo gli strumenti operativi. Le pagine vietate sono bloccate dal server, non solo nascoste dal menu.", st["body"]),
                       Spacer(1, 3 * mm), _ruoli(st, avail), Spacer(1, 4 * mm), _schema(kit_testi.FLUSSO_RUOLI, avail)]
        elif s.get("speciale") == "specifiche":
            blocco += [Paragraph("Per chi gestisce il server o vuole capire come è fatto il gestionale.", st["body"]), Spacer(1, 3 * mm), _kv(kit_testi.SPEC_TECNICHE, st, avail)]
        else:
            blocco += [Paragraph(esc(s["intro"]), st["body"]), Spacer(1, 3 * mm)]
            if s.get("passi"):
                blocco += [Paragraph("Come si fa", st["h2"]), _steps(s["passi"], st, avail)]
            if s.get("schema"):
                blocco += [Spacer(1, 3 * mm), Paragraph("Schema", st["h2"]), _schema(s["schema"], avail)]
            if s.get("tecnica"):
                blocco += [Spacer(1, 2 * mm), Paragraph("Dettagli tecnici", st["h2"])] + [Paragraph("• " + esc(x), st["small"]) for x in s["tecnica"]]
            if s.get("nota"):
                blocco += [Spacer(1, 3 * mm), _callout(s["nota"], st, avail)]
            if s.get("img"):
                im = _shot(shots, s["img"], st, avail, 85 * mm)
                if im is not None:
                    blocco += [Spacer(1, 4 * mm), im, Spacer(1, 1.5 * mm), Paragraph("Schermata di esempio con dati di prova (desktop a sinistra, telefono a destra).", st["cap"])]
        el += blocco
        if i < len(voci) - 1:
            el.append(PageBreak())
    doc.multiBuild(el)
    return path
