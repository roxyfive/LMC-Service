"""QR code del kit di consegna: QR1 = sito/app clienti, QR2 = accesso admin.

Due uscite: PNG ad alta risoluzione pronto da stampare (con titolo e indirizzo sotto) e il QR "nudo" da inserire nei PDF.
"""
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_Q

FONTS = Path(__file__).resolve().parent / "kit_assets" / "fonts"
ROSSO = (214, 40, 40)
SCURO = (22, 22, 28)


def qr_image(url, box=34, border=4):
    """QR nero su bianco (massimo contrasto per essere letto sempre), correzione errori livello Q."""
    q = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_Q, box_size=box, border=border)
    q.add_data(url)
    q.make(fit=True)
    return q.make_image(fill_color="black", back_color="white").convert("RGB")


def _font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def print_card(url, titolo, sottotitolo, out, logo=None):
    """PNG da stampare: titolo, QR grande, indirizzo. Circa 2400 x 3000 px (A4 a ~300 dpi con margini)."""
    w, h = 2400, 3000
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 330], fill=SCURO)
    d.rectangle([0, 330, w, 350], fill=ROSSO)
    if logo and Path(logo).exists():
        lg = Image.open(logo).convert("RGBA")
        lg.thumbnail((520, 220))
        img.paste(lg, (110, 55 + (220 - lg.height) // 2), lg)
    f_t, f_s, f_u = _font("Montserrat-ExtraBold.ttf", 118), _font("Inter-Regular.ttf", 62), _font("SpaceGrotesk-SemiBold.ttf", 66)
    d.text((w // 2, 560), titolo, font=f_t, fill=SCURO, anchor="mm")
    d.text((w // 2, 690), sottotitolo, font=f_s, fill=(90, 90, 100), anchor="mm")
    qr = qr_image(url, box=1, border=0)
    side = 1700
    qr = qr.resize((side, side), Image.NEAREST)
    x, y = (w - side) // 2, 840
    d.rectangle([x - 70, y - 70, x + side + 70, y + side + 70], outline=ROSSO, width=14)
    img.paste(qr, (x, y))
    d.text((w // 2, y + side + 190), url, font=f_u, fill=SCURO, anchor="mm")
    d.text((w // 2, h - 120), "Inquadra con la fotocamera del telefono", font=f_s, fill=(90, 90, 100), anchor="mm")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out, dpi=(300, 300))
    return out


def plain(url, out, box=20):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    qr_image(url, box=box).save(out)
    return out
