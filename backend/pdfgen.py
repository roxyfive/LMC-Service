import json
import tempfile
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from .config import ROOT

RED = colors.HexColor("#e10600")


def document_pdf(d, client, s):
    """PDF preventivo/fattura con logo LMC."""
    out = Path(tempfile.gettempdir()) / f"lmc_{d['number']}.pdf"
    c = canvas.Canvas(str(out), pagesize=A4)
    w, h = A4
    c.setFillColor(colors.HexColor("#0a0a0a"))
    c.rect(0, h - 45 * mm, w, 45 * mm, fill=1, stroke=0)
    logo = ROOT / "logo" / "logo.png"
    if logo.exists():
        c.drawImage(str(logo), 15 * mm, h - 42 * mm, width=70 * mm, height=39 * mm, preserveAspectRatio=True, mask="auto")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(w - 15 * mm, h - 22 * mm, d["kind"].upper())
    c.setFont("Helvetica", 11)
    c.drawRightString(w - 15 * mm, h - 30 * mm, f"N. {d['number']}  –  {d['date']}")
    y = h - 58 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "Da:")
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, y - 5 * mm, f"{s.get('brand', '')} – {s.get('owner', '')}")
    c.drawString(15 * mm, y - 10 * mm, f"{s.get('indirizzo', '')}  |  {s.get('telefono', '')}  |  {s.get('email', '')}".replace("[DA INSERIRE: email]", "").strip(" |"))
    if s.get("dati_societari"):      # ragione sociale / P.IVA inseriti da Admin > Testi
        c.drawString(15 * mm, y - 15 * mm, s["dati_societari"][:95])
    c.setFont("Helvetica-Bold", 10)
    c.drawString(110 * mm, y, "Per:")
    c.setFont("Helvetica", 10)
    if client:
        c.drawString(110 * mm, y - 5 * mm, client["name"] or "")
        c.drawString(110 * mm, y - 10 * mm, f"{client['phone'] or ''} {client['email'] or ''}")
    y -= 24 * mm
    c.setFillColor(RED)
    c.rect(15 * mm, y, w - 30 * mm, 7 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(17 * mm, y + 2 * mm, "Descrizione")
    c.drawRightString(125 * mm, y + 2 * mm, "Q.tà")
    c.drawRightString(150 * mm, y + 2 * mm, "Prezzo €")
    c.drawRightString(w - 17 * mm, y + 2 * mm, "Totale €")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    y -= 6 * mm
    for it in json.loads(d["items"] or "[]"):
        c.drawString(17 * mm, y, it["desc"][:70])
        c.drawRightString(125 * mm, y, f"{it['qty']:g}")
        c.drawRightString(150 * mm, y, f"{it['price']:.2f}")
        c.drawRightString(w - 17 * mm, y, f"{it['qty'] * it['price']:.2f}")
        y -= 6 * mm
        if y < 40 * mm:
            c.showPage()
            y = h - 30 * mm
            c.setFont("Helvetica", 9)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w - 17 * mm, y - 6 * mm, f"TOTALE: € {d['total']:.2f}")
    if d["notes"]:
        c.setFont("Helvetica", 9)
        c.drawString(15 * mm, y - 16 * mm, f"Note: {d['notes'][:110]}")
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(w / 2, 12 * mm, "La Music Company Service – Audio · Video · Luci – Napoli")
    c.save()
    return out
