"""Genera docs/Guida-SMTP-LMC.pdf: guida semplice (con diagramma) per chi deve attivare l'invio delle email del sito LMC.
Uso:  python -m tools.pdf_smtp [percorso_output.pdf]"""
import sys
from datetime import date
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle

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
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "Guida-SMTP-LMC.pdf"


def deco(c, doc):
    c.saveState()
    c.setFillColor(SCURO)
    c.rect(0, H - 20 * mm, W, 20 * mm, stroke=0, fill=1)
    c.setFillColor(ROSSO)
    c.rect(0, H - 20.8 * mm, W, 0.8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Mont", 11)
    c.drawString(M, H - 12.5 * mm, "LMC SERVICE")
    c.setFont("Inter", 8.5)
    c.setFillColor(colors.HexColor("#c5c5cf"))
    c.drawRightString(W - M, H - 12.5 * mm, "Guida: attivare le email del sito (SMTP)")
    c.setStrokeColor(BORDO)
    c.line(M, 14 * mm, W - M, 14 * mm)
    c.setFont("Inter", 8)
    c.setFillColor(GRIGIO)
    c.drawString(M, 9 * mm, f"La Music Company Service · guida del {date.today().strftime('%d/%m/%Y')}")
    c.drawRightString(W - M, 9 * mm, f"Pagina {doc.page}")
    c.restoreState()


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


el = []
# ---------------- pagina 1
el += [Paragraph("Attivare le email del sito LMC", h1), Paragraph("Guida semplice per l'agenzia (o per chi gestisce il server)", ParagraphStyle("sub", parent=body, fontSize=12, textColor=GRIGIO)), Spacer(1, 6 * mm),
       Paragraph("<b>In una frase.</b> Il sito di La Music Company Service è online e funziona, ma <b>non riesce a spedire email</b>: manca l'accesso a un servizio di posta (si chiama <b>SMTP</b>). "
                 "Finché non viene configurato, nessun cliente riceve conferme e Pasquale non riceve avvisi quando arriva una richiesta.", body), Spacer(1, 4 * mm),
       diagramma_flusso(), Spacer(1, 2 * mm),
       Paragraph("Cosa chiediamo all'agenzia", h2),
       Paragraph("1. <b>Scegliere</b> da quale casella di posta il sito deve spedire (consigliata: quella già usata da Pasquale, <b>lamusiccompany.24@gmail.com</b>).<br/>"
                 "2. <b>Procurare i dati di accesso</b> di quella casella (la tabella a pagina 3 dice esattamente quali).<br/>"
                 "3. <b>Inserirli sul server</b> (6 righe in un file) oppure passarli a chi ha accesso al server, in modo sicuro.<br/>"
                 "4. <b>Fare la prova</b>: una prenotazione di test deve generare una email di conferma.", body),
       PageBreak()]
# ---------------- pagina 2
el += [Paragraph("Che cos'è SMTP, in parole semplici", h1),
       Paragraph("Il sito non è una casella di posta: è un programma. Per spedire un'email deve consegnarla a un <b>server di posta</b>, come si porta una lettera all'ufficio postale. "
                 "Quel server si chiama <b>SMTP</b> e vuole sapere chi sei: per questo servono un <b>utente</b> e una <b>password</b>, esattamente come quando apri la tua posta.", body),
       Spacer(1, 3 * mm),
       Paragraph("Quali email spedisce il sito", h2),
       tabella([["A chi", "Quando", "Perché è importante"],
                ["Cliente", "Ha prenotato un appuntamento", "Conferma che la richiesta è arrivata"],
                ["Cliente", "Ha chiesto un preventivo", "Sa che è stato preso in carico"],
                ["Cliente", "Il giorno prima dell'appuntamento", "Promemoria: meno appuntamenti dimenticati"],
                ["Cliente", "Appuntamento confermato, spostato o annullato", "Resta informato senza telefonare"],
                ["Cliente", "Dopo l'evento", "Richiesta di recensione con link personale"],
                ["Pasquale", "Nuova prenotazione o nuovo preventivo", "Se non guarda il pannello, la richiesta resta ferma"],
                ["Pasquale", "Appuntamento annullato o spostato; nuova recensione da approvare", "Può reagire subito"],
                ["Pasquale", "Problema con il backup notturno", "Avviso di sicurezza"]],
               [26 * mm, 70 * mm, 78 * mm]),
       Spacer(1, 4 * mm),
       avviso("<b>Importante.</b> Oggi nessuna di queste email parte. Le richieste dei clienti <b>non si perdono</b>: restano salvate nel pannello Admin (Dashboard e Richieste), ma "
              "nessuno viene avvisato. Anche l'avviso WhatsApp (Twilio) non è attivo: l'email è l'unico avviso che si può attivare subito e senza costi.", ARANCIO, "#fff4e8"),
       PageBreak()]
# ---------------- pagina 3
el += [Paragraph("Cosa serve: i dati da procurare", h1),
       Paragraph("Il sito legge sei impostazioni dal file <font name='Mono'>.env</font> sul server. Ecco cosa significano e cosa scrivere.", body), Spacer(1, 3 * mm),
       tabella([["Impostazione", "Cosa è", "Esempio (Gmail)"],
                ["SMTP_HOST", "Indirizzo del server di posta", "smtp.gmail.com"],
                ["SMTP_PORT", "Porta. <b>Deve essere 587</b> (il sito usa il collegamento cifrato STARTTLS; la porta 465 non è supportata)", "587"],
                ["SMTP_USER", "Utente della casella (di solito l'indirizzo email completo)", "lamusiccompany.24@gmail.com"],
                ["SMTP_PASSWORD", "Password per i programmi (<b>non</b> quella normale, vedi sotto)", "16 lettere generate da Google"],
                ["MAIL_FROM", "Mittente che vedono i clienti. Con Gmail deve coincidere con SMTP_USER", "lamusiccompany.24@gmail.com"],
                ["OWNER_EMAIL", "Dove Pasquale riceve gli avvisi di nuove richieste", "lamusiccompany.24@gmail.com"]],
               [34 * mm, 82 * mm, 58 * mm]),
       Spacer(1, 5 * mm),
       Paragraph("Tre modi per avere l'account di posta (dal più semplice)", h2),
       tabella([["Opzione", "Come si fa", "Quando conviene"],
                ["A. Gmail di Pasquale", "Nell'account Google: Sicurezza › attivare la Verifica in due passaggi › «Password per le app» › creare una password (es. nome «Sito LMC»). Google mostra 16 lettere: sono la SMTP_PASSWORD.", "Subito e gratis. Limite circa 500 email al giorno: più che sufficiente"],
                ["B. Casella del vostro dominio o hosting", "Chiedere al provider i dati «SMTP in uscita» (server, porta 587 con STARTTLS, utente, password) e usarli al posto di quelli Gmail.", "Se avete un dominio con email (es. info@lamusiccompany.it): l'indirizzo mittente è più professionale"],
                ["C. Servizio di invio dedicato (es. Brevo, Mailgun)", "Creare un account, verificare il mittente, copiare le credenziali SMTP.", "Se in futuro si spediscono molte email. Richiede un dominio proprio"]],
               [40 * mm, 84 * mm, 50 * mm]),
       Spacer(1, 4 * mm),
       avviso("<b>Sicurezza.</b> La password <b>non va scritta in email, in chat o nei documenti</b>: va inserita solo nel file .env sul server (che è leggibile solo dal servizio). "
              "Va comunicata a voce o con uno strumento per password, mai in chiaro. Una password per le app si può revocare in qualsiasi momento senza cambiare quella dell'account."),
       PageBreak()]
# ---------------- pagina 4
el += [Paragraph("Per chi ha accesso al server: passi tecnici", h1),
       Paragraph("Il sito gira su una VPS Ubuntu (IONOS) nella cartella <font name='Mono'>/srv/lmc</font>. Servono i permessi di amministratore (root).", body), Spacer(1, 3 * mm),
       Paragraph("1. Apri il file delle impostazioni", h2), codice("sudo nano /srv/lmc/.env"),
       Paragraph("2. Aggiungi (o compila) queste righe, con i VOSTRI valori", h2),
       codice("SMTP_HOST=smtp.gmail.com\nSMTP_PORT=587\nSMTP_USER=lamusiccompany.24@gmail.com\nSMTP_PASSWORD=<la password per le app, senza spazi>\nMAIL_FROM=lamusiccompany.24@gmail.com\nOWNER_EMAIL=lamusiccompany.24@gmail.com"),
       Paragraph("Salva con Ctrl+O, Invio, Ctrl+X. Niente spazi attorno al segno =, niente commenti sulla stessa riga.", small),
       Paragraph("3. Riavvia il sito", h2), codice("sudo systemctl restart lmc"),
       Paragraph("4. Prova", h2),
       Paragraph("Dal sito (<font name='Mono'>https://lmcservice.duckdns.org</font>) fai una <b>prenotazione di prova</b> con un tuo indirizzo email: devono arrivare l'email di conferma al cliente e l'avviso a OWNER_EMAIL (controlla anche la cartella Spam la prima volta). "
                 "Per vedere subito eventuali errori:", body),
       codice("sudo tail -n 20 /srv/lmc/data/outbox.log"),
       Paragraph("Se compare una riga <font name='Mono'>ERRORE invio a ...</font> il motivo è scritto accanto (vedi tabella). Se non ci sono errori e le email arrivano, è fatto.", body),
       Paragraph("Se qualcosa non va", h2),
       tabella([["Messaggio nel log", "Significa", "Cosa fare"],
                ["Authentication failed / 535", "Utente o password sbagliati", "Rigenerare la password per le app, ricopiarla senza spazi"],
                ["Application-specific password required", "Si è usata la password normale", "Usare la password per le app (richiede la Verifica in due passaggi)"],
                ["Connection timed out / refused", "Server o porta sbagliati, oppure bloccati", "Controllare SMTP_HOST e SMTP_PORT=587"],
                ["STARTTLS extension not supported", "Quel server non supporta STARTTLS sulla 587", "Usare un server/provider che lo supporta (il sito non usa la 465)"],
                ["Le email arrivano in Spam", "Il mittente non è «autenticato»", "Con Gmail raramente succede; con dominio proprio servono i record SPF, DKIM e DMARC del provider"]],
               [52 * mm, 56 * mm, 66 * mm]),
       Paragraph("Per dubbi scrivere a chi ha realizzato il sito (FiveTech) indicando l'ultima riga di <font name='Mono'>outbox.log</font>, <b>senza mai includere la password</b>.", small)]

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUT), pagesize=(W, H), leftMargin=M, rightMargin=M, topMargin=28 * mm, bottomMargin=20 * mm, title="Attivare le email del sito LMC (SMTP)", author="FiveTech", subject="Guida SMTP")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(M, 20 * mm, W - 2 * M, H - 48 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=deco)])
doc.build(el)
print(OUT)
