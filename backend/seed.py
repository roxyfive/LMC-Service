import os
import json
import random
import secrets
import sqlite3
from datetime import date, timedelta
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from werkzeug.security import generate_password_hash
from .config import ROOT, DB_PATH, UPLOADS, MODE, CATEGORIES
from .media import save_image_obj

PLACEHOLDERS = [("Palco rosso", "Eventi"), ("Fasci in movimento", "Luci"), ("Regia audio", "Audio"),
                ("Show demo", "Show Demo"), ("Ledwall", "Video"), ("Progetto palco", "Progettazione"),
                ("Meeting aziendale", "Meeting"), ("Serata evento", "Eventi"), ("Light show", "Luci"),
                ("Impianto line array", "Audio"), ("Concerto", "Show Demo"), ("Allestimento", "Progettazione")]


def make_placeholder(idx, label, w=1600, h=1000):
    rnd = random.Random(idx * 7 + 3)
    im = Image.new("RGB", (w, h), (8, 8, 10))
    beams = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(beams)
    for _ in range(rnd.randint(5, 9)):
        x = rnd.randint(0, w)
        spread = rnd.randint(80, 260)
        tx = x + rnd.randint(-500, 500)
        col = (rnd.randint(170, 255), rnd.randint(0, 30), rnd.randint(0, 20))
        d.polygon([(x - 6, 0), (x + 6, 0), (tx + spread, h * 0.85), (tx - spread, h * 0.85)], fill=col)
    beams = beams.filter(ImageFilter.GaussianBlur(40))
    im = Image.blend(im, beams, 0.85)
    floor = Image.new("RGB", (w, h // 5), (30, 0, 0))
    im.paste(floor, (0, h - h // 5))
    im = im.filter(ImageFilter.GaussianBlur(2))
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", 54)
        f2 = ImageFont.truetype("arial.ttf", 26)
    except OSError:
        f = f2 = ImageFont.load_default()
    d.text((w / 2, h / 2 - 20), label.upper(), fill=(255, 255, 255), font=f, anchor="mm")
    d.text((w / 2, h / 2 + 40), "FOTO IN ARRIVO", fill=(225, 6, 0), font=f2, anchor="mm")
    return im


def seed():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # impostazioni di default (solo se mancanti)
    base = json.loads((ROOT / "contenuti" / "testi.json").read_text(encoding="utf-8"))
    for k, v in base.items():
        if k in ("servizi", "intro_righe"):
            v = json.dumps(v, ensure_ascii=False)
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('slot_minutes','60')")
    # dati reali del cliente: sostituiscono solo i segnaposto, mai ciò che l'admin ha già modificato
    for k in ("telefono", "whatsapp", "orari", "zone"):
        cur.execute("UPDATE settings SET value=? WHERE key=? AND (value='' OR value LIKE '[DA%' OR (key='zone' AND value LIKE 'Tutta Italia%'))",
                    (base[k], k))
    cur.execute("UPDATE settings SET value=? WHERE key='servizi' AND value LIKE '%Impianti audio per eventi, meeting e show.%'",
                (json.dumps(base["servizi"], ensure_ascii=False),))
    # team: il titolare è precaricato, il resto si gestisce da Admin > Team e Contatti
    if not cur.execute("SELECT 1 FROM team").fetchone():
        cur.execute("INSERT INTO team(name,role,phone,email,note,visible,sort,notify,on_duty) VALUES(?,?,?,?,?,?,?,?,?)",
                    ("Pasquale", "Titolare", base["telefono"], "", "Aperto 24 ore", "si", 0, "si", "si"))
    # una tantum: nei DB creati prima di notifiche/turni, il titolare risulta di turno e riceve le notifiche
    if not cur.execute("SELECT 1 FROM settings WHERE key='migr_team_duty'").fetchone():
        if not cur.execute("SELECT 1 FROM team WHERE on_duty='si'").fetchone():
            cur.execute("UPDATE team SET on_duty='si' WHERE id=(SELECT MIN(id) FROM team)")
        cur.execute("INSERT INTO settings(key,value) VALUES('migr_team_duty','1')")
    # admin: password da .env solo al primo avvio, altrimenti casuale mostrata una volta
    if not cur.execute("SELECT 1 FROM admin_users").fetchone():
        user = os.getenv("ADMIN_USER", "admin")
        pw = os.getenv("ADMIN_PASSWORD") or secrets.token_urlsafe(9)
        cur.execute("INSERT INTO admin_users(username,pw_hash) VALUES(?,?)", (user, generate_password_hash(pw)))
        if not os.getenv("ADMIN_PASSWORD"):
            print(f"\n=== PRIMO AVVIO: utente admin '{user}' password generata: {pw}  (annotala, non verrà più mostrata) ===\n")
    # disponibilità di default: lun-ven 10-13 e 16-19
    if not cur.execute("SELECT 1 FROM availability").fetchone():
        for wd in range(5):
            cur.execute("INSERT INTO availability(weekday,start,end) VALUES(?,?,?)", (wd, "10:00", "13:00"))
            cur.execute("INSERT INTO availability(weekday,start,end) VALUES(?,?,?)", (wd, "16:00", "19:00"))
    # foto segnaposto (nessuna foto reale recuperata)
    if not cur.execute("SELECT 1 FROM media").fetchone():
        UPLOADS.mkdir(exist_ok=True)
        for i, (label, cat) in enumerate(PLACEHOLDERS):
            base_name = secrets.token_hex(16)
            save_image_obj(make_placeholder(i, label), base_name)
            cur.execute("""INSERT INTO media(filename,kind,title,caption,category,show_home,show_gallery,show_intro,featured,sort,source,placeholder)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,1)""",
                        (base_name, "image", f"[Segnaposto] {label}", "Sostituisci con una foto reale dall'admin", cat,
                         1, 1, 1 if i < 6 else 0, 1 if i == 0 else 0, i, "generata localmente"))
    # dati DEMO (solo modalità demo, solo se vuoto)
    if MODE == "demo" and not cur.execute("SELECT 1 FROM clients").fetchone():
        today = date.today()
        cur.executemany("INSERT INTO clients(name,phone,email,notes) VALUES(?,?,?,?)", [
            ("DEMO Mario Rossi", "3330000001", "demo1@example.com", "Dato finto"),
            ("DEMO Anna Verdi", "3330000002", "demo2@example.com", "Dato finto"),
            ("DEMO Ristorante Il Faro", "3330000003", "demo3@example.com", "Dato finto")])
        cur.executemany("INSERT INTO suppliers(name,category,phone,email,notes) VALUES(?,?,?,?,?)", [
            ("DEMO Cavi & Co", "Cavi", "0810000001", "forn1@example.com", "Dato finto"),
            ("DEMO Trasporti Sud", "Trasporti", "0810000002", "forn2@example.com", "Dato finto")])
        cur.executemany("INSERT INTO equipment(name,category,qty,status,notes) VALUES(?,?,?,?,?)", [
            ("DEMO Line array 12\"", "audio", 8, "disponibile", ""), ("DEMO Mixer digitale", "audio", 2, "disponibile", ""),
            ("DEMO Moving head beam", "luci", 12, "disponibile", ""), ("DEMO Ledwall modulo", "video", 30, "in uso", "")])
        cur.executemany("INSERT INTO events(title,date,place,client_id,notes) VALUES(?,?,?,?,?)", [
            ("DEMO Matrimonio Rossi", (today + timedelta(days=12)).isoformat(), "Napoli", 1, "Dato finto"),
            ("DEMO Meeting aziendale", (today + timedelta(days=25)).isoformat(), "Roma", 3, "Dato finto")])
        cur.executemany("INSERT INTO journal(date,description,type,amount,notes) VALUES(?,?,?,?,?)", [
            (today.isoformat(), "DEMO Acconto matrimonio", "entrata", 500, ""),
            (today.isoformat(), "DEMO Noleggio furgone", "uscita", 120, "")])
        cur.execute("INSERT INTO appointments(token,name,phone,email,event_type,event_date,notes,slot_date,slot_time,status,consent) VALUES(?,?,?,?,?,?,?,?,?,?,1)",
                    (secrets.token_urlsafe(8), "DEMO Cliente", "3330000009", "demo9@example.com", "Matrimonio",
                     (today + timedelta(days=60)).isoformat(), "Dato finto", (today + timedelta(days=3)).isoformat(), "10:00", "in attesa"))
        cur.execute("INSERT INTO quotes(name,phone,email,event_type,event_date,place,guests,services,notes,consent) VALUES(?,?,?,?,?,?,?,?,?,1)",
                    ("DEMO Richiedente", "3330000008", "demo8@example.com", "Festa privata",
                     (today + timedelta(days=40)).isoformat(), "Napoli", "150", "Audio, Luci", "Dato finto"))
    con.commit()
    con.close()
