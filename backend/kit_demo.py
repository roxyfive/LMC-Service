"""Dati DI PROVA (nomi e importi inventati) per gli screenshot dei tutorial e della guida. NON usare su un sito reale:
`python -m backend.kit_consegna` li carica solo in un database temporaneo, mai in quello di produzione."""
import json
from datetime import date, timedelta

from . import billing
from .db import q, ex, set_setting


def populate():
    today = date.today()
    d = lambda n: (today + timedelta(days=n)).isoformat()
    set_setting("fat_ragione", "La Music Company Service di Pasquale Toppi")
    set_setting("fat_piva", "01234567890")
    set_setting("fat_cf", "TPPPQL90A01F839X")
    set_setting("fat_sede", "Via dei Fari 12, 80100 Napoli (NA)")
    set_setting("fat_iban", "IT60X0542811101000000123456")
    set_setting("fat_pec", "lmcservice@pec.example")
    clients = {}
    for key, name, mail, addr, piva in [("hotel", "Hotel Villa Aurora", "eventi@villaaurora.example", "Via Posillipo 80, 80123 Napoli", "09876543210"),
                                        ("rossi", "Rossi Eventi Srl", "info@rossieventi.example", "Via Toledo 210, 80134 Napoli", "12345678901"),
                                        ("sposi", "Giulia Esposito", "giulia@example.com", "Via Chiaia 5, 80121 Napoli", ""),
                                        ("club", "Club Mediterraneo", "booking@clubmed.example", "Lungomare Caracciolo 3, Napoli", "11122233344")]:
        clients[key] = ex("INSERT INTO clients(name,phone,email,address,piva) VALUES(?,?,?,?,?)", (name, "081 555 01 23", mail, addr, piva))
    tar = {"Impianto audio per eventi (casse + mixer + microfoni)": 450, "Ledwall": 55, "Luci per la serata (set base)": 300, "Allestimento palco": 380,
           "Tecnico / fonico": 40, "Trasporto e montaggio/smontaggio": 120}
    for n, p in tar.items():
        ex("UPDATE tariffe SET price=?, active=1, public=? WHERE name=?", (p, 1 if p in (450, 300, 380) else 0, n))
    # richieste e appuntamenti
    for i, (n, ev, svc, st) in enumerate([("Valentina Greco", "Matrimonio", "Audio, Luci, Allestimenti", "nuova"), ("Studio Bianchi", "Evento aziendale / Meeting", "Audio, Video", "nuova"),
                                          ("Antonio Ferri", "Festa privata", "Luci, Audio", "in lavorazione"), ("Elena Russo", "Concerto / Show", "Audio, Luci, Video", "confermata")]):
        ex("INSERT INTO quotes(name,phone,email,event_type,event_date,place,guests,services,notes,status,consent) VALUES(?,?,?,?,?,?,?,?,?,?,1)",
           (n, "333 100 20 3%d" % i, n.split()[0].lower() + "@example.com", ev, d(18 + i * 9), "Napoli", str(80 + i * 40), svc, "Richiesta dal sito", st))
    for i, (n, ev, off, t, st) in enumerate([("Valentina Greco", "Matrimonio", 0, "10:00", "confermato"), ("Studio Bianchi", "Evento aziendale / Meeting", 0, "16:00", "in attesa"),
                                             ("Marco De Luca", "Festa privata", 2, "11:00", "in attesa"), ("Sara Conte", "Discoteca / Locale", 4, "17:00", "confermato")]):
        ex("INSERT INTO appointments(token,name,phone,email,event_type,event_date,notes,slot_date,slot_time,status,consent) VALUES(?,?,?,?,?,?,?,?,?,?,1)",
           (f"demo{i}", n, "333 400 50 6%d" % i, n.split()[0].lower() + "@example.com", ev, d(30 + i * 5), "Vorremmo vedere il palco", d(off), t, st))
    for dow in range(0, 5):
        ex("INSERT INTO availability(weekday,start,end) VALUES(?,?,?)", (dow, "10:00", "13:00"))
        ex("INSERT INTO availability(weekday,start,end) VALUES(?,?,?)", (dow, "16:00", "19:00"))
    ex("INSERT INTO closures(date,note) VALUES(?,?)", (d(6), "Ferie"))
    ex("INSERT INTO day_notes(date,note,user) VALUES(?,?,?)", (d(0), "Controllare le batterie dei radiomicrofoni", "admin"))
    # eventi
    evs = {}
    for k, (t, off, place, cl, typ, st) in {"gala": ("Gala di fine anno", -3, "Hotel Villa Aurora", "hotel", "Evento aziendale / Meeting", "svolto"),
                                           "nozze": ("Matrimonio Esposito", 14, "Castello Aragonese", "sposi", "Matrimonio", "confermato"),
                                           "live": ("Live Estate al Club", 7, "Club Mediterraneo", "club", "Concerto / Show", "confermato"),
                                           "conv": ("Convention Rossi", 25, "Mostra d'Oltremare", "rossi", "Evento aziendale / Meeting", "confermato")}.items():
        evs[k] = ex("INSERT INTO events(title,date,place,client_id,event_type,status,notes) VALUES(?,?,?,?,?,?,?)", (t, d(off), place, clients[cl], typ, st, ""))
    for name, cat, qty, stt in [("Cassa attiva 15\"", "audio", 8, "disponibile"), ("Mixer digitale 32 canali", "audio", 2, "disponibile"), ("Testa mobile LED", "luci", 12, "disponibile"),
                                ("Barra LED", "luci", 16, "in uso"), ("Ledwall modulo 50x50", "video", 40, "disponibile"), ("Radiomicrofono", "audio", 6, "in riparazione")]:
        ex("INSERT INTO equipment(name,category,qty,status) VALUES(?,?,?,?)", (name, cat, qty, stt))
    # preventivi, fatture, acconti: incassi sparsi sull'anno per il grafico
    items = lambda *a: [{"desc": x, "qty": y, "price": z} for x, y, z in a]
    did = ex("INSERT INTO documents(kind,number,client_id,date,items,total,status,notes) VALUES('preventivo',?,?,?,?,?,'accettato','Matrimonio Esposito')",
             (billing.prev_number(), clients["sposi"], d(-10), json.dumps(items(("Impianto audio", 1, 450), ("Luci scenografiche", 1, 300), ("Allestimento palco", 1, 380)), ensure_ascii=False), 1130))
    billing.add_payment(300, "bonifico", "Acconto alla conferma", d(-9), document_id=did, user="admin")
    ex("INSERT INTO documents(kind,number,client_id,date,items,total,status) VALUES('preventivo',?,?,?,?,?,'inviato')",
       (billing.prev_number(), clients["rossi"], d(-4), json.dumps(items(("Impianto audio", 2, 450), ("Ledwall", 12, 55), ("Tecnico / fonico", 16, 40)), ensure_ascii=False), 2200))
    specs = [("hotel", -90, [("Service audio e luci gala", 1, 1200)], "pagata"), ("rossi", -70, [("Convention: audio e video", 1, 1850)], "pagata"),
             ("club", -40, [("Live: impianto e luci", 1, 950)], "parziale"), ("hotel", -35, [("Gala di fine anno", 1, 1600)], "scaduta"), ("rossi", -5, [("Allestimento", 1, 780)], "emessa"),
             ("sposi", 0, [("Matrimonio Esposito", 1, 1130)], "bozza")]
    for cl, off, it, st in specs:
        i = billing.new_invoice(clients[cl], [{"desc": a, "qty": b, "price": c} for a, b, c in it], "", user="admin")
        ex("UPDATE invoices SET issue_date=? WHERE id=?", (d(off), i))
        if st != "bozza":
            billing.issue_invoice(i, "admin")
            if st == "scaduta":
                ex("UPDATE invoices SET due_date=? WHERE id=?", (d(off + 20), i))
            elif st == "emessa":
                pass
        inv = q("SELECT * FROM invoices WHERE id=?", (i,), one=True)
        if st == "pagata":
            billing.add_payment(inv["total"], "bonifico", "Saldo", d(off + 12), invoice_id=i, user="admin")
        elif st == "parziale":
            billing.add_payment(round(inv["total"] * 0.4, 2), "contanti", "Acconto", d(off + 3), invoice_id=i, user="admin")
    for off, amt in [(-300, 700), (-270, 1100), (-240, 600), (-210, 1500), (-180, 900), (-150, 1700), (-120, 2300)]:
        billing.add_payment(amt, "bonifico", "Storico", d(off), event_id=evs["gala"], user="admin")
    # recensioni
    for a, ev, tx, st in [("Hotel Villa Aurora", "Gala di fine anno", "Professionali e puntuali: audio perfetto per tutta la serata.", "approvata"),
                          ("Giulia E.", "Matrimonio", "Hanno curato ogni dettaglio di luci e musica. Consigliatissimi!", "in attesa")]:
        ex("INSERT INTO reviews(author,text,source,hidden,status,stars,event,created) VALUES(?,?,?,?,?,5,?,datetime('now'))", (a, tx, "dal sito", 0 if st == "approvata" else 1, st, ev))
    return clients, evs
