"""Fatture, acconti e incassi: calcoli, numerazione progressiva e PDF.

Regole (semplici e verificabili):
  · il prezzo di ogni voce è IMPONIBILE (IVA esclusa); IVA % configurabile (default 22);
  · la fattura nasce «bozza» (senza numero); il numero progressivo si assegna SOLO quando la si emette (niente buchi nella numerazione);
  · una fattura emessa non si elimina: si annulla;
  · gli incassi sono la tabella `payments` (acconti e saldi): «pagata» = acconti ≥ totale; segnare «pagata» a mano registra il saldo residuo;
  · «scaduta» non è uno stato salvato: è una fattura emessa/parziale con scadenza passata e residuo > 0.
"""
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .config import ROOT
from .db import q, ex, get_db, get_setting

RED = colors.HexColor("#e10600")
INK = colors.HexColor("#16161c")
GREY = colors.HexColor("#6b6f7a")
LINE = colors.HexColor("#dcdde2")
SOFT = colors.HexColor("#f4f4f6")

METHODS = ["bonifico", "contanti", "carta", "assegno", "altro"]
SDI_STATES = ["non inviata", "inviata", "consegnata", "scartata", "mancata consegna"]


def eur(x):
    """1234.5 -> '1.234,50' (formato italiano)."""
    try:
        s = f"{float(x or 0):,.2f}"
    except (TypeError, ValueError):
        s = "0.00"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def num(txt, default=0.0):
    try:
        return float(str(txt).replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")) if "," in str(txt) else float(str(txt).replace(" ", ""))
    except ValueError:
        return default


# ------------------------------------------------------------------ impostazioni fiscali
FISCAL_FIELDS = [
    ("fat_ragione", "Ragione sociale", "text"), ("fat_piva", "Partita IVA", "text"), ("fat_cf", "Codice fiscale", "text"),
    ("fat_sede", "Sede legale (via, CAP, città, provincia)", "text"), ("fat_iban", "IBAN per i bonifici", "text"),
    ("fat_pec", "PEC", "text"), ("fat_sdi", "Codice destinatario SDI (se hai un intermediario)", "text"),
    ("fat_regime", "Dicitura di regime / esenzione IVA (facoltativa, es. «Regime forfettario art.1 c.54-89 L.190/2014»)", "text"),
    ("fat_prefix", "Prefisso numerazione (es. F oppure FT)", "text"), ("fat_next", "Prossimo numero da usare quest'anno (es. 1)", "number"),
    ("fat_digits", "Cifre del numero (3 → 001)", "number"), ("fat_reset", "Numerazione che riparte da 1 ogni anno", "select:si,no"),
    ("fat_iva", "IVA predefinita %", "number"), ("fat_giorni", "Scadenza predefinita (giorni dall'emissione)", "number"),
    ("fat_piede", "Nota a piè di fattura (facoltativa)", "area"),
]
FISCAL_DEFAULT = {"fat_prefix": "F", "fat_next": "1", "fat_digits": "3", "fat_reset": "si", "fat_iva": "22", "fat_giorni": "30"}


def fiscal():
    d = {k: (get_setting(k, "") or FISCAL_DEFAULT.get(k, "")) for k, _l, _t in FISCAL_FIELDS}
    d["fat_ragione"] = d["fat_ragione"] or get_setting("brand", "")
    return d


def fiscal_missing():
    f = fiscal()
    return [l for k, l, _t in FISCAL_FIELDS if k in ("fat_piva", "fat_sede") and not f[k].strip()]


# ------------------------------------------------------------------ calcoli
def parse_items(descs, qtys, prices):
    items = []
    for d, qn, pr in zip(descs, qtys, prices):
        d = (d or "").strip()
        if not d:
            continue
        items.append({"desc": d[:160], "qty": num(qn, 1.0) or 1.0, "price": num(pr, 0.0)})
    return items


def totals(items, iva_pct):
    imp = round(sum(i["qty"] * i["price"] for i in items), 2)
    iva = round(imp * float(iva_pct or 0) / 100.0, 2)
    return imp, iva, round(imp + iva, 2)


def paid_of(kind, i):
    col = {"invoice": "invoice_id", "document": "document_id", "event": "event_id"}[kind]
    return round(q(f"SELECT COALESCE(SUM(amount),0) s FROM payments WHERE {col}=?", (i,), one=True)["s"], 2)


def invoice_view(inv):
    """Dizionario pronto per i template: totali, incassato, residuo e stato mostrato (bozza/emessa/parziale/scaduta/pagata/annullata)."""
    d = dict(inv)
    paid = paid_of("invoice", inv["id"])
    resid = round((inv["total"] or 0) - paid, 2)
    st = inv["status"]
    show = st
    today = date.today().isoformat()
    if st in ("emessa", "pagata"):
        if resid <= 0.005 and (inv["total"] or 0) > 0:
            show = "pagata"
        elif paid > 0:
            show = "parziale"
        else:
            show = "emessa"
        if show in ("emessa", "parziale") and inv["due_date"] and inv["due_date"] < today:
            show = "scaduta"
    d.update(paid=paid, resid=resid, show=show, items_l=json.loads(inv["items"] or "[]"))
    return d


def sync_invoice_status(i):
    """Dopo ogni acconto: emessa ↔ pagata in base al residuo."""
    inv = q("SELECT * FROM invoices WHERE id=?", (i,), one=True)
    if not inv or inv["status"] not in ("emessa", "pagata"):
        return
    resid = (inv["total"] or 0) - paid_of("invoice", i)
    new = "pagata" if resid <= 0.005 and (inv["total"] or 0) > 0 else "emessa"
    if new != inv["status"]:
        ex("UPDATE invoices SET status=? WHERE id=?", (new, i))


def add_payment(amount, method="bonifico", note="", day=None, invoice_id=None, document_id=None, event_id=None, user=""):
    pid = ex("INSERT INTO payments(date,amount,method,note,invoice_id,document_id,event_id,created_by) VALUES(?,?,?,?,?,?,?,?)",
             (day or date.today().isoformat(), round(float(amount), 2), method if method in METHODS else "altro", note[:200], invoice_id, document_id, event_id, user))
    if invoice_id:
        sync_invoice_status(invoice_id)
    return pid


def delete_payment(pid):
    p = q("SELECT * FROM payments WHERE id=?", (pid,), one=True)
    if p:
        ex("DELETE FROM payments WHERE id=?", (pid,))
        if p["invoice_id"]:
            sync_invoice_status(p["invoice_id"])


def mark_paid(i, user=""):
    inv = invoice_view(q("SELECT * FROM invoices WHERE id=?", (i,), one=True))
    if inv["resid"] > 0.005:
        add_payment(inv["resid"], "bonifico", "Saldo (fattura segnata come pagata)", invoice_id=i, user=user)
    else:
        sync_invoice_status(i)


# ------------------------------------------------------------------ numerazione
def next_number(year=None):
    f = fiscal()
    year = year or date.today().year
    digits = max(1, min(8, int(num(f["fat_digits"], 3))))
    start = max(1, int(num(f["fat_next"], 1)))
    if f["fat_reset"] == "no":
        last = q("SELECT COALESCE(MAX(seq),0) m FROM invoices WHERE number IS NOT NULL AND number!=''", one=True)["m"]
    else:
        last = q("SELECT COALESCE(MAX(seq),0) m FROM invoices WHERE year=? AND number IS NOT NULL AND number!=''", (year,), one=True)["m"]
    seq = max(last + 1, start)
    return seq, f"{f['fat_prefix']}{year}-{seq:0{digits}d}"


def issue_invoice(i, user=""):
    """Assegna il numero progressivo (in transazione, senza buchi né doppioni) e porta la fattura da bozza a emessa."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        inv = db.execute("SELECT * FROM invoices WHERE id=?", (i,)).fetchone()
        if not inv or inv["status"] != "bozza":
            db.rollback()
            return None
        issue = inv["issue_date"] or date.today().isoformat()
        year = int(issue[:4])
        seq, number = next_number(year)
        days = int(num(fiscal()["fat_giorni"], 30))
        due = inv["due_date"] or (date.fromisoformat(issue) + timedelta(days=days)).isoformat()
        db.execute("UPDATE invoices SET number=?,year=?,seq=?,status='emessa',issue_date=?,due_date=? WHERE id=?", (number, year, seq, issue, due, i))
        db.commit()
        return number
    except Exception:
        db.rollback()
        raise


def prev_number():
    year = date.today().year
    pre = get_setting("prev_prefix", "P") or "P"
    last = 0
    for r in q("SELECT number FROM documents WHERE kind='preventivo' AND number LIKE ?", (f"{pre}{year}-%",)):
        try:
            last = max(last, int(r["number"].rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            pass
    return f"{pre}{year}-{last + 1:03d}"


# ------------------------------------------------------------------ creazione da pratiche esistenti
def client_for(name, phone="", email=""):
    """Cliente esistente (stessa email o telefono) oppure nuovo."""
    r = None
    if email:
        r = q("SELECT * FROM clients WHERE lower(email)=lower(?)", (email,), one=True)
    if not r and phone:
        r = q("SELECT * FROM clients WHERE phone=?", (phone,), one=True)
    if r:
        return r["id"]
    return ex("INSERT INTO clients(name,phone,email,notes) VALUES(?,?,?,?)", (name, phone, email, "Creato dal gestionale"))


def snapshot_client(cid):
    c = q("SELECT * FROM clients WHERE id=?", (cid,), one=True) if cid else None
    if not c:
        return dict(client_name="", client_addr="", client_piva="", client_cf="", client_sdi="", client_pec="")
    return dict(client_name=c["name"] or "", client_addr=c["address"] or "", client_piva=c["piva"] or "", client_cf=c["cf"] or "",
                client_sdi=c["sdi_code"] or "", client_pec=c["pec"] or "")


def new_invoice(client_id, items, notes="", source_type="", source_id=None, event_id=None, iva_pct=None, user=""):
    f = fiscal()
    pct = float(f["fat_iva"] or 22) if iva_pct is None else float(iva_pct)
    imp, iva, tot = totals(items, pct)
    s = snapshot_client(client_id)
    return ex("""INSERT INTO invoices(client_id,client_name,client_addr,client_piva,client_cf,client_sdi,client_pec,issue_date,items,imponibile,iva_pct,iva,total,
                 notes,source_type,source_id,event_id,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (client_id, s["client_name"], s["client_addr"], s["client_piva"], s["client_cf"], s["client_sdi"], s["client_pec"], date.today().isoformat(),
               json.dumps(items, ensure_ascii=False), imp, pct, iva, tot, notes[:500], source_type, source_id, event_id, user))


# ------------------------------------------------------------------ PDF
def _wrap(c, text, font, size, width):
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if c.stringWidth(t, font, size) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def invoice_pdf(inv, out=None):
    """PDF elegante: intestazione scura con logo, dati del cedente (da Admin), cliente, righe, imponibile/IVA/totale, scadenza e IBAN."""
    v = invoice_view(inv)
    f = fiscal()
    out = Path(out or Path(tempfile.gettempdir()) / f"lmc_fattura_{inv['id']}.pdf")
    c = canvas.Canvas(str(out), pagesize=A4)
    w, h = A4
    M = 16 * mm

    def header(first=True):
        c.setFillColor(INK)
        c.rect(0, h - 40 * mm, w, 40 * mm, fill=1, stroke=0)
        c.setFillColor(RED)
        c.rect(0, h - 41.6 * mm, w, 1.6 * mm, fill=1, stroke=0)
        logo = ROOT / "logo" / "logo.png"
        if logo.exists():
            c.drawImage(str(logo), M, h - 37 * mm, width=58 * mm, height=33 * mm, preserveAspectRatio=True, mask="auto")
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 22)
        label = "FATTURA" if v["status"] != "bozza" else "FATTURA (bozza)"
        if v["status"] == "annullata":
            label = "FATTURA ANNULLATA"
        c.drawRightString(w - M, h - 18 * mm, label)
        c.setFont("Helvetica", 11)
        c.drawRightString(w - M, h - 26 * mm, f"N. {v['number'] or '—'}")
        c.drawRightString(w - M, h - 32 * mm, f"Data {_it(v['issue_date'])}")

    def _it(d):
        return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d and len(d) >= 10 else (d or "")

    header()
    y = h - 52 * mm
    # cedente / cliente
    c.setFillColor(GREY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(M, y, "CEDENTE / PRESTATORE")
    c.drawString(w / 2 + 4 * mm, y, "CLIENTE")
    c.setFillColor(INK)
    yy = y - 5 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, yy, (f["fat_ragione"] or get_setting("brand", ""))[:48])
    c.setFont("Helvetica", 9)
    for ln in [f"P.IVA {f['fat_piva']}" if f["fat_piva"] else "", f"C.F. {f['fat_cf']}" if f["fat_cf"] else "", f["fat_sede"],
               f"PEC {f['fat_pec']}" if f["fat_pec"] else "", f"{get_setting('telefono', '')}  {get_setting('email', '')}".strip()]:
        if ln:
            yy -= 4.6 * mm
            c.drawString(M, yy, ln[:70])
    if not (f["fat_piva"] or f["fat_sede"]) and get_setting("dati_societari", ""):
        yy -= 4.6 * mm
        c.drawString(M, yy, get_setting("dati_societari", "")[:70])
    cy = y - 5 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(w / 2 + 4 * mm, cy, (v["client_name"] or "—")[:40])
    c.setFont("Helvetica", 9)
    for ln in [v["client_addr"], f"P.IVA {v['client_piva']}" if v["client_piva"] else "", f"C.F. {v['client_cf']}" if v["client_cf"] else "",
               f"Cod. destinatario {v['client_sdi']}" if v["client_sdi"] else "", f"PEC {v['client_pec']}" if v["client_pec"] else ""]:
        if ln:
            cy -= 4.6 * mm
            c.drawString(w / 2 + 4 * mm, cy, ln[:52])
    y = min(yy, cy) - 10 * mm
    # tabella righe
    def thead(yv):
        c.setFillColor(INK)
        c.rect(M, yv, w - 2 * M, 7.5 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(M + 3 * mm, yv + 2.5 * mm, "DESCRIZIONE")
        c.drawRightString(w - M - 62 * mm, yv + 2.5 * mm, "Q.TÀ")
        c.drawRightString(w - M - 33 * mm, yv + 2.5 * mm, "PREZZO")
        c.drawRightString(w - M - 3 * mm, yv + 2.5 * mm, "IMPORTO")
        return yv - 1 * mm
    y = thead(y)
    shade = False
    for it in v["items_l"]:
        lines = _wrap(c, it["desc"], "Helvetica", 9, w - 2 * M - 86 * mm)
        rowh = max(7 * mm, 4.4 * mm * len(lines) + 2.6 * mm)
        if y - rowh < 62 * mm:
            c.showPage()
            header()
            y = thead(h - 52 * mm)
        shade = not shade
        if shade:
            c.setFillColor(SOFT)
            c.rect(M, y - rowh, w - 2 * M, rowh, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Helvetica", 9)
        for n, ln in enumerate(lines):
            c.drawString(M + 3 * mm, y - 5 * mm - n * 4.4 * mm, ln)
        c.drawRightString(w - M - 62 * mm, y - 5 * mm, f"{it['qty']:g}")
        c.drawRightString(w - M - 33 * mm, y - 5 * mm, eur(it["price"]))
        c.drawRightString(w - M - 3 * mm, y - 5 * mm, eur(it["qty"] * it["price"]))
        y -= rowh
    c.setStrokeColor(LINE)
    c.line(M, y, w - M, y)
    # totali
    if y < 70 * mm:
        c.showPage()
        header()
        y = h - 60 * mm
    ty = y - 8 * mm
    bx = w - M - 78 * mm
    c.setFont("Helvetica", 10)
    c.setFillColor(GREY)
    c.drawString(bx, ty, "Imponibile")
    c.drawRightString(w - M - 3 * mm, ty, f"€ {eur(v['imponibile'])}")
    c.drawString(bx, ty - 6 * mm, f"IVA {v['iva_pct']:g}%")
    c.drawRightString(w - M - 3 * mm, ty - 6 * mm, f"€ {eur(v['iva'])}")
    c.setFillColor(RED)
    c.rect(bx - 3 * mm, ty - 20 * mm, 81 * mm, 10 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(bx, ty - 16.8 * mm, "TOTALE")
    c.drawRightString(w - M - 3 * mm, ty - 16.8 * mm, f"€ {eur(v['total'])}")
    if v["paid"] > 0:
        c.setFillColor(INK)
        c.setFont("Helvetica", 9)
        c.drawString(bx, ty - 26 * mm, "Già versato")
        c.drawRightString(w - M - 3 * mm, ty - 26 * mm, f"€ {eur(v['paid'])}")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(bx, ty - 32 * mm, "Residuo da pagare")
        c.drawRightString(w - M - 3 * mm, ty - 32 * mm, f"€ {eur(max(v['resid'], 0))}")
    # pagamento
    py = ty
    c.setFillColor(GREY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(M, py, "PAGAMENTO")
    c.setFillColor(INK)
    c.setFont("Helvetica", 9)
    py -= 5 * mm
    if v["due_date"]:
        c.drawString(M, py, f"Scadenza: {_it(v['due_date'])}")
        py -= 4.6 * mm
    if f["fat_iban"]:
        c.drawString(M, py, f"Bonifico a: {f['fat_ragione'][:34]}")
        py -= 4.6 * mm
        c.drawString(M, py, f"IBAN {f['fat_iban']}")
        py -= 4.6 * mm
    note = " ".join(x for x in [v["notes"], f["fat_regime"]] if x)
    if note:
        py -= 3 * mm
        c.setFillColor(GREY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(M, py, "NOTE")
        c.setFillColor(INK)
        c.setFont("Helvetica", 8.5)
        for ln in _wrap(c, note, "Helvetica", 8.5, 98 * mm)[:6]:
            py -= 4.2 * mm
            c.drawString(M, py, ln)
    if v["show"] == "pagata":
        c.saveState()
        c.setFillColor(colors.Color(0.1, 0.55, 0.25, alpha=0.18))
        c.setFont("Helvetica-Bold", 60)
        c.translate(w / 2, h / 2)
        c.rotate(25)
        c.drawCentredString(0, 0, "PAGATA")
        c.restoreState()
    # piede
    c.setFillColor(GREY)
    c.setFont("Helvetica", 7.5)
    foot = f["fat_piede"] or "Copia di cortesia: la fattura elettronica valida ai fini fiscali è quella trasmessa tramite il Sistema di Interscambio (SDI)."
    for n, ln in enumerate(_wrap(c, foot, "Helvetica", 7.5, w - 2 * M)[:2]):
        c.drawCentredString(w / 2, 14 * mm - n * 3.6 * mm, ln)
    c.setFillColor(RED)
    c.rect(0, 0, w, 3 * mm, fill=1, stroke=0)
    c.save()
    return out


def quote_pdf(d, client, s):
    """Preventivo: stesso impianto grafico della fattura, senza IVA (importi indicativi, su misura)."""
    from .pdfgen import document_pdf
    return document_pdf(d, client, s)
