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
    c.drawRightString(W - M, H - 17 * mm, "Guida per l'agenzia: email e dominio .it")
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
    c.drawString(M, y - 26 * mm, "e dominio .it")
    c.setFillColor(GRIGIO)
    c.setFont("Inter", 12)
    c.drawString(M, y - 37 * mm, "Due completamenti per il sito di La Music Company Service")
    # scheda dati
    c.setStrokeColor(BORDO)
    c.setFillColor(CHIARO)
    c.roundRect(M, y - 76 * mm, W - 2 * M, 28 * mm, 3 * mm, stroke=1, fill=1)
    righe = [("Destinatario", "Agenzia pubblicitaria / chi gestisce il server di La Music Company Service"), ("Contenuto", "A. email del sito (SMTP) · B. dominio .it, se Pasquale Toppi aderisce"),
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
    d = Drawing(174 * mm, 118 * mm)
    L = 174 * mm
    # riga alta: cliente -> sito -> server di posta -> destinatari
    box(d, 0, 78 * mm, 36 * mm, 28 * mm, "1. Il cliente", ["compila il modulo", "sul sito", "(prenota / preventivo)"], colors.HexColor("#3a3a44"))
    box(d, 46 * mm, 78 * mm, 38 * mm, 28 * mm, "2. Sito LMC", ["(il nostro server)", "prepara l'email", "e la consegna"], SCURO)
    box(d, 94 * mm, 78 * mm, 38 * mm, 28 * mm, "3. Server SMTP", ["è «l'ufficio postale»", "(es. Gmail)", "che spedisce davvero"], ROSSO)
    box(d, 142 * mm, 78 * mm, 32 * mm, 28 * mm, "4. Chi riceve", ["il cliente: conferma", "Pasquale: avviso", "di nuova richiesta"], VERDE)
    for x1, x2 in ((36, 46), (84, 94), (132, 142)):
        freccia(d, x1 * mm, 92 * mm, x2 * mm, 92 * mm)
    d.add(String(0, 111 * mm, "COME FUNZIONA (con SMTP attivo)", fontName="Inter-Bold", fontSize=9.5, fillColor=VERDE))
    # riga bassa: senza SMTP
    d.add(String(0, 62 * mm, "COME È ORA (SMTP non configurato)", fontName="Inter-Bold", fontSize=9.5, fillColor=ARANCIO))
    box(d, 46 * mm, 22 * mm, 38 * mm, 28 * mm, "Sito LMC", ["l'email non può", "uscire dal server"], SCURO)
    box(d, 94 * mm, 22 * mm, 80 * mm, 28 * mm, "Resta in un file sul server", ["data/outbox.log", "nessuno lo legge: nessuna email arriva"], ARANCIO)
    freccia(d, 84 * mm, 36 * mm, 94 * mm, 36 * mm, ARANCIO)
    box(d, 0, 22 * mm, 36 * mm, 28 * mm, "Il cliente", ["compila il modulo", "e non riceve niente"], colors.HexColor("#3a3a44"))
    freccia(d, 36 * mm, 36 * mm, 46 * mm, 36 * mm, ARANCIO)
    d.add(String(0, 8 * mm, "Cosa serve per passare dalla riga arancione a quella verde: un account di posta da cui spedire (il punto 3) e 6 righe di impostazioni.", fontName="Inter", fontSize=8.6, fillColor=GRIGIO))
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
    d = Drawing(174 * mm, 66 * mm)
    d.add(String(0, 62 * mm, "TABELLA DI MARCIA", fontName="Inter-Bold", fontSize=9.5, fillColor=ROSSO))
    flusso(d, 30 * mm, [("FASE 1", ["Email del sito", "(SMTP)", "15 minuti"], VERDE), ("FASE 2", ["Dominio .it", "solo se Pasquale", "aderisce"], ROSSO),
                        ("FASE 3", ["Sito sul nuovo", "indirizzo con", "HTTPS"], SCURO), ("FASE 4", ["Email col dominio", "(info@...) e", "rifiniture"], colors.HexColor("#3a3a44"))], h=27 * mm)
    d.add(String(0, 22 * mm, "La Fase 1 si può fare subito e da sola. Le Fasi 2-4 dipendono dalla decisione di Pasquale Toppi sul dominio.", fontName="Inter", fontSize=8.6, fillColor=GRIGIO))
    d.add(String(0, 14 * mm, "Fino al completamento il sito resta online e funzionante su lmcservice.duckdns.org (HTTPS valido, backup notturno attivo).", fontName="Inter", fontSize=8.6, fillColor=GRIGIO))
    return d


def diagramma_dominio():
    d = Drawing(174 * mm, 52 * mm)
    flusso(d, 14 * mm, [("1. Registrar", ["registra il dominio", ".it a nome di", "Pasquale Toppi"], colors.HexColor("#3a3a44")),
                        ("2. DNS", ["il dominio punta", "all'IP del server", "(record A)"], ROSSO),
                        ("3. Server VPS", ["nginx + certificato", "HTTPS (Let's", "Encrypt)"], SCURO),
                        ("4. Sito online", ["https://www.", "dominio.it", "con lucchetto"], VERDE)], h=28 * mm)
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
el = [Spacer(1, 1), NextPageTemplate("p"), PageBreak()]
# ---- p.1 panoramica
el += [Paragraph("Dove siamo e cosa resta da fare", h1), Paragraph("Per l'agenzia pubblicitaria di La Music Company Service", ParagraphStyle("sub", parent=body, fontSize=12, textColor=GRIGIO)), Spacer(1, 5 * mm),
       Paragraph("Il sito di La Music Company Service è <b>online e funziona</b>: vetrina con video e galleria, prenotazioni e preventivi, area riservata per Pasquale e i collaboratori, backup automatico ogni notte. "
                 "Mancano due completamenti, che questa guida spiega passo per passo.", body), Spacer(1, 4 * mm),
       tabella([["Già fatto", "Da completare"],
                ["Sito su <b>https://lmcservice.duckdns.org</b> con HTTPS valido<br/>Area Admin con ruoli (titolare / collaboratori)<br/>Fatture, acconti, agenda, recensioni, statistiche<br/>Privacy, cookie, accessibilità a norma<br/>Backup cifrato ogni notte (anche su cloud)",
                 "<b>A. Email del sito (SMTP)</b>: oggi nessuna email parte<br/><b>B. Dominio .it</b>: indirizzo professionale al posto di «duckdns.org» (solo se Pasquale Toppi aderisce)"]],
               [87 * mm, 87 * mm]),
       Spacer(1, 4 * mm), diagramma_marcia(), Spacer(1, 2 * mm),
       Paragraph("La decisione di Pasquale Toppi", h2),
       Paragraph("Il dominio .it è intestato a una persona o a un'azienda: <b>deve essere Pasquale Toppi</b> (il titolare), non l'agenzia. Per questo serve il suo consenso prima di procedere.", body), Spacer(1, 2 * mm),
       casella("<b>Aderisco</b>: procedere con il dominio .it (Fasi 2, 3 e 4) intestato a mio nome."), Spacer(1, 1.5 * mm),
       casella("<b>Non ora</b>: per il momento restiamo su lmcservice.duckdns.org e facciamo solo la Fase 1 (email)."), Spacer(1, 4 * mm),
       Paragraph("Firma ________________________________      Data ____________________", small),
       PageBreak()]
# ---- capitolo A
el += [Paragraph("A. Email del sito (SMTP)", h1),
       Paragraph("<b>Fase 1 · si può fare subito · circa 15 minuti</b>", ParagraphStyle("f", parent=body, textColor=VERDE)), Spacer(1, 2 * mm),
       Paragraph("Il sito non è una casella di posta: è un programma. Per spedire un'email deve consegnarla a un <b>server di posta</b>, come si porta una lettera all'ufficio postale. Quel server si chiama <b>SMTP</b> e vuole sapere chi sei: per questo servono un <b>utente</b> e una <b>password</b>.", body), Spacer(1, 3 * mm),
       ridim(diagramma_flusso(), 0.8), Spacer(1, 1 * mm),
       Paragraph("Quali email spedisce il sito", h2),
       tabella([["A chi", "Quando", "Perché è importante"],
                ["Cliente", "Ha prenotato un appuntamento o chiesto un preventivo", "Conferma che la richiesta è arrivata"],
                ["Cliente", "Il giorno prima dell'appuntamento", "Promemoria: meno appuntamenti dimenticati"],
                ["Cliente", "Appuntamento confermato, spostato o annullato", "Resta informato senza telefonare"],
                ["Cliente", "Dopo l'evento", "Richiesta di recensione con link personale"],
                ["Pasquale", "Nuova prenotazione, nuovo preventivo, annullamenti, nuova recensione", "Se non guarda il pannello, la richiesta resta ferma"],
                ["Pasquale", "Problema con il backup notturno", "Avviso di sicurezza"]],
               [26 * mm, 80 * mm, 68 * mm]),
       Spacer(1, 3 * mm),
       avviso("<b>Oggi nessuna di queste email parte.</b> Le richieste non si perdono (restano nel pannello Admin) ma nessuno viene avvisato e il cliente non riceve conferme. Anche l'avviso WhatsApp (Twilio) non è attivo: l'email è l'avviso più semplice e senza costi.", ARANCIO, "#fff4e8"),
       PageBreak()]
el += [Paragraph("A. Cosa serve: i dati da procurare", h1),
       Paragraph("Il sito legge sei impostazioni dal file <font name='Mono'>.env</font> sul server.", body), Spacer(1, 3 * mm),
       tabella([["Impostazione", "Cosa è", "Esempio (Gmail)"],
                ["SMTP_HOST", "Indirizzo del server di posta", "smtp.gmail.com"],
                ["SMTP_PORT", "Porta. <b>Deve essere 587</b> (collegamento cifrato STARTTLS; la 465 non è supportata)", "587"],
                ["SMTP_USER", "Utente della casella (di solito l'indirizzo completo)", "lamusiccompany.24@gmail.com"],
                ["SMTP_PASSWORD", "Password per i programmi (<b>non</b> quella normale)", "16 lettere generate da Google"],
                ["MAIL_FROM", "Mittente che vedono i clienti (con Gmail uguale a SMTP_USER)", "lamusiccompany.24@gmail.com"],
                ["OWNER_EMAIL", "Dove Pasquale riceve gli avvisi", "lamusiccompany.24@gmail.com"]],
               [34 * mm, 82 * mm, 58 * mm]),
       Spacer(1, 5 * mm), Paragraph("Tre modi per avere l'account di posta (dal più semplice)", h2),
       tabella([["Opzione", "Come si fa", "Quando conviene"],
                ["A. Gmail di Pasquale", "Account Google › Sicurezza › Verifica in due passaggi › «Password per le app» › crearne una (es. «Sito LMC»): sono 16 lettere.", "Subito e gratis. Circa 500 email al giorno: più che sufficienti"],
                ["B. Casella del vostro dominio o hosting", "Chiedere al provider i dati «SMTP in uscita» (server, porta 587 STARTTLS, utente, password).", "Dopo la Fase 2-3: mittente professionale (info@dominio.it)"],
                ["C. Servizio di invio dedicato (es. Brevo, Mailgun)", "Creare un account, verificare il mittente, copiare le credenziali SMTP.", "Se in futuro si spediscono molte email. Richiede il dominio"]],
               [40 * mm, 84 * mm, 50 * mm]),
       Spacer(1, 4 * mm),
       avviso("<b>Sicurezza.</b> La password <b>non va scritta in email, chat o documenti</b>: va inserita solo nel file .env sul server. Va comunicata a voce o con uno strumento per password. Una password per le app si può revocare in qualsiasi momento senza toccare la password dell'account."),
       PageBreak()]
el += [Paragraph("A. Passi tecnici sul server", h1),
       Paragraph("Il sito gira su una VPS Ubuntu (IONOS) in <font name='Mono'>/srv/lmc</font>. Servono i permessi di amministratore (root).", body), Spacer(1, 2 * mm),
       Paragraph("1. Apri il file delle impostazioni", h2), codice("sudo nano /srv/lmc/.env"),
       Paragraph("2. Aggiungi (o compila) queste righe, con i VOSTRI valori", h2),
       codice("SMTP_HOST=smtp.gmail.com\nSMTP_PORT=587\nSMTP_USER=lamusiccompany.24@gmail.com\nSMTP_PASSWORD=<la password per le app, senza spazi>\nMAIL_FROM=lamusiccompany.24@gmail.com\nOWNER_EMAIL=lamusiccompany.24@gmail.com"),
       Paragraph("Salva con Ctrl+O, Invio, Ctrl+X. Niente spazi attorno al segno =, niente commenti sulla stessa riga.", small),
       Paragraph("3. Riavvia il sito", h2), codice("sudo systemctl restart lmc"),
       Paragraph("4. Prova", h2),
       Paragraph("Dal sito fai una <b>prenotazione di prova</b> con un tuo indirizzo email: devono arrivare la conferma al cliente e l'avviso a OWNER_EMAIL (controlla anche lo Spam la prima volta). Per vedere subito eventuali errori:", body),
       codice("sudo tail -n 20 /srv/lmc/data/outbox.log"),
       Paragraph("Se compare <font name='Mono'>ERRORE invio a ...</font> il motivo è scritto accanto. Se non ci sono errori e le email arrivano, la Fase 1 è finita.", body), Spacer(1, 2 * mm),
       Paragraph("Se qualcosa non va", h2),
       tabella([["Messaggio nel log", "Significa", "Cosa fare"],
                ["Authentication failed / 535", "Utente o password sbagliati", "Rigenerare la password per le app, ricopiarla senza spazi"],
                ["Application-specific password required", "Si è usata la password normale", "Usare la password per le app"],
                ["Connection timed out / refused", "Server o porta sbagliati o bloccati", "Controllare SMTP_HOST e SMTP_PORT=587"],
                ["STARTTLS extension not supported", "Quel server non supporta STARTTLS sulla 587", "Usare un provider che lo supporta"],
                ["Le email arrivano in Spam", "Il mittente non è «autenticato»", "Con Gmail raro; con dominio proprio servono SPF, DKIM e DMARC (capitolo B)"]],
               [52 * mm, 56 * mm, 66 * mm]),
       PageBreak()]
# ---- capitolo B
el += [Paragraph("B. Dominio .it", h1),
       Paragraph("<b>Fasi 2, 3 e 4 · solo se Pasquale Toppi aderisce</b>", ParagraphStyle("f", parent=body, textColor=ROSSO)), Spacer(1, 2 * mm),
       Paragraph("Oggi il sito risponde a <b>lmcservice.duckdns.org</b>: funziona, ma è un indirizzo di servizio gratuito. Un dominio <b>.it</b> (per esempio <font name='Mono'>www.lamusiccompany.it</font>: il nome è solo un esempio, lo sceglie Pasquale) dà più fiducia ai clienti, serve per stampare QR e biglietti da visita che durano nel tempo e permette email professionali come <font name='Mono'>info@lamusiccompany.it</font>.", body), Spacer(1, 3 * mm),
       diagramma_dominio(), Spacer(1, 2 * mm),
       Paragraph("Cosa serve", h2),
       tabella([["Cosa", "Dettaglio"],
                ["Consenso di Pasquale Toppi", "Il dominio è intestato al titolare (registrante): non all'agenzia. Se un giorno cambia agenzia, il dominio resta suo."],
                ["Dati del titolare", "Nome e cognome, codice fiscale (o P.IVA), indirizzo, email e telefono. Sono dati professionali: li inserisce Pasquale, non vanno copiati altrove."],
                ["Registrar", "Un fornitore accreditato per i .it (per esempio lo stesso IONOS della VPS, oppure un altro a scelta). Il costo è annuale e basso: chiedere il prezzo aggiornato al fornitore."],
                ["Requisito .it", "Il registrante deve essere cittadino o avere sede in uno Stato dello Spazio economico europeo."],
                ["Nome del dominio", "Breve, facile da dettare al telefono, coerente con il marchio. Verificare che sia libero prima di decidere."]],
               [46 * mm, 128 * mm]),
       Spacer(1, 3 * mm),
       avviso("<b>Importante.</b> Le credenziali del registrar (e il codice di trasferimento «AuthCode») restano a Pasquale. L'agenzia lavora con un accesso delegato o con le istruzioni di questa guida, senza intestarsi il dominio.", ARANCIO, "#fff4e8"),
       PageBreak()]
el += [Paragraph("B. Dal dominio al sito online: i passi", h1),
       tabella([["#", "Chi", "Cosa fa", "Tempo"],
                ["1", "Pasquale", "Decide il nome e registra il dominio .it a suo nome presso il registrar scelto", "10 minuti"],
                ["2", "Agenzia", "Nel pannello DNS del registrar crea due record <b>A</b> verso l'IP della VPS (tabella sotto): uno per <font name='Mono'>@</font> (il dominio nudo) e uno per <font name='Mono'>www</font>", "5 minuti"],
                ["3", "Agenzia", "Aspetta la propagazione DNS e controlla con <font name='Mono'>ping www.dominio.it</font> che mostri l'IP della VPS", "da minuti a 24-48 ore"],
                ["4", "Tecnico (sul server)", "Collega il dominio: configura nginx e il certificato HTTPS con il comando sotto", "5 minuti"],
                ["5", "Tecnico", "Aggiorna <font name='Mono'>PUBLIC_URL</font> nel .env e, in Admin › Testi, «Sito ufficiale – URL»", "5 minuti"],
                ["6", "Insieme", "Verifica finale con lo script <font name='Mono'>verifica-online.sh</font> e prova dal telefono (lucchetto, video, prenotazione)", "10 minuti"]],
               [8 * mm, 32 * mm, 106 * mm, 28 * mm]),
       Spacer(1, 4 * mm),
       Paragraph("Record DNS da creare", h2),
       tabella([["Tipo", "Nome", "Valore", "Note"],
                ["A", "@", "87.106.219.112", "IP della VPS IONOS (da riconfermare prima di creare il record)"],
                ["A", "www", "87.106.219.112", "Stesso IP"]],
               [18 * mm, 24 * mm, 48 * mm, 84 * mm]),
       Spacer(1, 4 * mm),
       Paragraph("Comando sul server (passo 4)", h2),
       codice("sudo bash /srv/lmc/deploy/collega-dominio.sh www.DOMINIO.it email@esempio.it\nbash /srv/lmc/deploy/verifica-online.sh https://www.DOMINIO.it"),
       Paragraph("L'email serve a Let's Encrypt per avvisare se il certificato sta per scadere (si rinnova da solo). Sostituire DOMINIO.it con il dominio scelto.", small), Spacer(1, 3 * mm),
       avviso("<b>Cosa succede al vecchio indirizzo.</b> Dopo il collegamento il server risponde solo al nuovo dominio: <b>lmcservice.duckdns.org smette di aprirsi</b>. Prima di staccarlo va quindi preparato un reindirizzamento automatico, così i vecchi link e QR continuano a funzionare. Lo prepara chi ha realizzato il sito (FiveTech): avvisarlo prima del passo 4.", ARANCIO, "#fff4e8"),
       PageBreak()]
el += [Paragraph("B. Fase 4: email col dominio e rifiniture", h1),
       Paragraph("Con il dominio proprio si può avere una casella professionale (per esempio <font name='Mono'>info@lamusiccompany.it</font>) e spedire dal sito con quella.", body), Spacer(1, 3 * mm),
       Paragraph("Record per far arrivare le email in posta in arrivo (non in Spam)", h2),
       tabella([["Record", "A cosa serve", "Chi li fornisce"],
                ["SPF (tipo TXT)", "Dice quali server possono spedire a nome del dominio", "Il provider della casella email"],
                ["DKIM (tipo TXT o CNAME)", "Firma digitale delle email: dimostra che non sono falsificate", "Il provider della casella email"],
                ["DMARC (tipo TXT)", "Dice cosa fare delle email che non passano i controlli (iniziare con «p=none», poi irrigidire)", "Si scrive una volta sola; l'agenzia può prepararlo"]],
               [44 * mm, 84 * mm, 46 * mm]),
       Spacer(1, 3 * mm),
       Paragraph("Rifiniture da fare dopo il passaggio al dominio", h2),
       tabella([["Cosa", "Perché"],
                ["Rigenerare i <b>QR code</b> del kit di consegna con il nuovo indirizzo (comando <font name='Mono'>python -m backend.kit_consegna --url https://www.DOMINIO.it</font>)", "I QR stampati puntano al vecchio indirizzo: finché il reindirizzamento resta attivo funzionano, ma i nuovi vanno stampati con quello definitivo"],
                ["Aggiornare i link nelle bio di Instagram, Facebook, TikTok e nella scheda Google Business", "Il traffico dai social arrivi sul nuovo indirizzo"],
                ["Admin › Testi › «Sito ufficiale – URL» e PUBLIC_URL nel .env", "Servono ai link nelle email (recensioni) e ai dati strutturati per Google"],
                ["Aggiornare mittente e SMTP con la casella del dominio (Opzione B del capitolo A)", "Email più professionali e meno Spam"],
                ["Rieseguire <font name='Mono'>verifica-online.sh</font>", "Conferma che HTTPS, cookie sicuri e backup sono a posto con il nuovo indirizzo"]],
               [96 * mm, 78 * mm]),
       Spacer(1, 4 * mm),
       Paragraph("Checklist finale", h2),
       casella("Fase 1: email del sito funzionanti (prenotazione di prova ricevuta)"), Spacer(1, 1 * mm),
       casella("Pasquale Toppi ha deciso sul dominio .it (firma a pagina 2)"), Spacer(1, 1 * mm),
       casella("Dominio registrato a nome di Pasquale Toppi e record DNS creati"), Spacer(1, 1 * mm),
       casella("Reindirizzamento del vecchio indirizzo preparato, poi sito collegato al dominio con HTTPS"), Spacer(1, 1 * mm),
       casella("Email col dominio (SPF, DKIM, DMARC) e QR/social aggiornati"), Spacer(1, 4 * mm),
       Paragraph("Per dubbi scrivere a chi ha realizzato il sito (FiveTech), <b>senza mai includere password</b>.", small)]

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUT), pagesize=(W, H), leftMargin=M, rightMargin=M, topMargin=28 * mm, bottomMargin=20 * mm, title="Guida per l'agenzia: email del sito e dominio .it", author="FiveTech", subject="Guida agenzia")
fr = Frame(M, 20 * mm, W - 2 * M, H - 48 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="cover", frames=[Frame(M, 20 * mm, W - 2 * M, H - 40 * mm, id="c")], onPage=copertina), PageTemplate(id="p", frames=[fr], onPage=deco)])
doc.build(el, canvasmaker=NumberedCanvas)
print(OUT)
