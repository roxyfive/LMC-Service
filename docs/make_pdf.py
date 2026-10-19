"""Genera i PDF di spiegazione: docs/Guida_Clienti.pdf e docs/Guida_Admin.pdf (intestazione FiveTech).
Uso: python docs/make_pdf.py"""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, ListFlowable, ListItem

ROOT = Path(__file__).resolve().parent.parent
FT = ROOT / "logo" / "fivetech.png"
RED = colors.HexColor("#e10600")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=22, textColor=colors.HexColor("#0a0a0a"), spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=14, textColor=RED, spaceBefore=12, spaceAfter=4)
P = ParagraphStyle("p", parent=ss["BodyText"], fontSize=10.5, leading=15)
NOTE = ParagraphStyle("n", parent=P, backColor=colors.HexColor("#fff3f2"), borderPadding=6, textColor=colors.HexColor("#7a0c08"))


def page(c, d):
    w, h = A4
    c.setFillColor(colors.HexColor("#0a0a0a"))
    c.rect(0, h - 28 * mm, w, 28 * mm, fill=1, stroke=0)
    if FT.exists():
        c.drawImage(str(FT), 12 * mm, h - 26 * mm, width=44 * mm, height=24 * mm, preserveAspectRatio=True, mask="auto")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(w - 15 * mm, h - 14 * mm, d.title_text)
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 15 * mm, h - 20 * mm, "Realizzato da FiveTech per La Music Company Service")
    c.setFillColor(RED)
    c.rect(0, h - 29.5 * mm, w, 1.5 * mm, fill=1, stroke=0)
    c.setFillColor(colors.grey)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, 10 * mm, f"LMC Service · Napoli · pagina {c.getPageNumber()}")


def steps(items):
    return ListFlowable([ListItem(Paragraph(t, P), leftIndent=14) for t in items], bulletType="1", leftIndent=14)


def bullets(items):
    return ListFlowable([ListItem(Paragraph(t, P), leftIndent=14) for t in items], bulletType="bullet", leftIndent=14)


def build(path, title, story):
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=36 * mm, bottomMargin=18 * mm)
    doc.title_text = title
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)], onPage=page)])
    doc.build(story)
    print("creato", path.name)


clienti = [
    Paragraph("Come prenotare e usare l'app LMC Service", H1),
    Paragraph("Guida semplice per i clienti: appuntamenti, preventivi e assistente virtuale.", P),
    Paragraph("1. Prenotare un appuntamento", H2),
    steps(["Apri il sito e vai alla sezione <b>Prenota</b> (o premi il pulsante rosso in alto).",
           "Scegli il <b>giorno</b>: compaiono solo gli orari liberi.",
           "Scegli l'<b>orario</b>, scrivi nome, telefono ed email, il tipo di evento e le eventuali note.",
           "Spunta il consenso privacy e premi <b>Conferma appuntamento</b>.",
           "Ricevi un'email di conferma con un link personale."]),
    Paragraph("2. Modificare o annullare", H2),
    Paragraph("Apri il link che trovi nell'email: puoi <b>spostare</b> l'appuntamento scegliendo un nuovo orario libero oppure <b>annullarlo</b>. Il giorno prima riceverai un promemoria (se l'appuntamento è confermato).", P),
    Paragraph("3. Richiedere un preventivo", H2),
    steps(["Vai alla sezione <b>Richiedi un preventivo</b>.",
           "Indica tipo di evento, data, luogo, numero di ospiti e i servizi che ti interessano (audio, luci, video, progettazione).",
           "Invia: la richiesta arriva direttamente a LMC Service, che ti risponderà."]),
    Paragraph("4. L'assistente virtuale (tutti i giorni, a ogni ora)", H2),
    bullets(["Premi <b>Assistente</b> in basso a destra.", "Scrivi la domanda oppure premi il microfono e parla in italiano.",
             "Puoi ascoltare la risposta (opzione «Risposta vocale»).",
             "Se l'assistente non conosce un'informazione ti indirizza ai contatti: non inventa mai risposte."]),
    Paragraph("5. Installare l'app sul telefono", H2),
    bullets(["<b>Android (Chrome)</b>: premi «Installa» quando compare il riquadro, oppure menu ⋮ → Installa app.",
             "<b>iPhone (Safari)</b>: pulsante Condividi → Aggiungi alla schermata Home."]),
    Spacer(1, 8),
    Paragraph("I tuoi dati sono usati solo per rispondere alla richiesta. Per cancellarli scrivi ai contatti del sito.", NOTE),
]

admin = [
    Paragraph("Guida per l'amministratore", H1),
    Paragraph("Come gestire agenda, disponibilità, foto, testi, gestionale e backup. Pannello: <b>https://tuodominio/admin</b>.", P),
    Paragraph("1. Accesso", H2),
    Paragraph("Inserisci utente e password. La password è salvata solo come <i>hash</i>; dopo 5 tentativi errati l'accesso si blocca per 5 minuti. Per uscire usa «Esci» in alto a destra. Il badge DEMO/PRODUZIONE indica la modalità (impostata in .env).", P),
    Paragraph("2. Agenda e richieste", H2),
    bullets(["<b>Agenda</b>: appuntamenti futuri e prossimi eventi; pulsanti <i>Conferma</i> / <i>Annulla</i> (al cliente parte un'email).",
             "<b>Richieste</b>: tutti gli appuntamenti e i preventivi ricevuti; cambia lo stato (nuova, in lavorazione, inviata, chiusa) o crea il cliente con «+ Cliente»."]),
    Paragraph("3. Disponibilità", H2),
    steps(["Imposta la <b>durata</b> di ogni appuntamento (minuti).", "Aggiungi le <b>fasce settimanali</b> (giorno + dalle/alle).",
           "Aggiungi i <b>giorni di chiusura</b> (ferie, festivi): quel giorno non è prenotabile."]),
    Paragraph("4. Foto e video", H2),
    steps(["Apri <b>Foto e video</b>. Trascina i file nel riquadro oppure premi «Scegli file» (dal telefono puoi scattare o scegliere dalla galleria, più file insieme).",
           "Scegli la categoria (Eventi, Show Demo, Audio, Luci, Video, Progettazione, Meeting) e premi Carica: l'ottimizzazione è automatica (WebP, più dimensioni, rotazione corretta).",
           "Per ogni foto: titolo, didascalia, categoria e dove mostrarla (<b>Home</b>, <b>Galleria</b>, <b>Intro</b>). «Hero» la usa come immagine principale.",
           "<b>Nascondi</b> toglie la foto dal sito senza cancellarla; <b>Elimina</b> la cancella (con conferma).",
           "Per riordinare, trascina le card. Limiti: immagini 12 MB, video 60 MB; solo jpg/png/webp e mp4/webm."]),
    Paragraph("Le immagini con badge SEGNAPOSTO sono provvisorie: sostituiscile con foto reali.", NOTE),
    Paragraph("5. Testi", H2),
    Paragraph("In <b>Testi</b> modifichi claim, storia, servizi, contatti, orari, link social, informativa privacy e le frasi dell'intro (una per riga). Salva con «Salva tutto». I campi [DA INSERIRE] vanno completati. In <b>Dicono di noi</b> inserisci solo recensioni reali.", P),
    Paragraph("6. Gestionale", H2),
    bullets(["<b>Clienti</b> e <b>Fornitori</b>: anagrafiche con note.",
             "<b>Magazzino</b>: attrezzature audio/luci/video con quantità e stato.",
             "<b>Eventi</b>: calendario eventi; aprendo un evento assegni le attrezzature (quantità).",
             "<b>Preventivi/Fatture</b>: scegli cliente, scrivi le voci (<i>descrizione;quantità;prezzo</i>, una per riga) e scarica il <b>PDF con logo</b>.",
             "<b>Prima nota</b>: entrate e uscite con saldo."]),
    Paragraph("7. Backup e ripristino", H2),
    Paragraph("Ogni notte il VPS salva database e foto in /var/backups/lmc (14 giorni). Per ripristinare: ferma il servizio, estrai l'archivio in <i>data/</i> e riavvia (vedi DEPLOY.md). Copia i backup anche fuori dal VPS.", P),
    Paragraph("8. Assistente telefonico (predisposto)", H2),
    Paragraph("La voce al telefono non è attiva. Le tabelle e il webhook sono pronti: si attiva in .env quando deciderai il fornitore voce.", P),
]

if __name__ == "__main__":
    out = ROOT / "docs"
    build(out / "Guida_Clienti.pdf", "Guida per i clienti", clienti)
    build(out / "Guida_Admin.pdf", "Guida amministratore", admin)
