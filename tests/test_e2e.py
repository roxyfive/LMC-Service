"""Test end-to-end: python -m tests.test_e2e  (usa ADMIN_PASSWORD dall'ambiente)"""
import io
import os
import re
import tempfile
from datetime import date, timedelta
from PIL import Image

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_test_")  # DB isolato: non tocca data/
os.environ.setdefault("ADMIN_PASSWORD", "TestLocale123")
from backend import create_app
from backend.db import q

PW = os.environ["ADMIN_PASSWORD"]
app = create_app()
c = app.test_client()
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


def csrf(html):
    m = re.search(r'name="csrf" content="([0-9a-f]+)"', html) or re.search(r'name="csrf" value="([0-9a-f]+)"', html)
    return m.group(1)


home = c.get("/").get_data(as_text=True)
check("home 200 + SEO", "LocalBusiness" in home and "og:title" in home and 'lang="it"' in home)
tok = csrf(home)
H = {"X-CSRF-Token": tok}

# prenotazione completa
d = date.today() + timedelta(days=1)
while d.weekday() > 4:
    d += timedelta(days=1)
slots = c.get(f"/api/slots?date={d}").get_json()
check("slot disponibili", len(slots) > 0, slots)
body = {"name": "Test Cliente", "phone": "3331112222", "email": "t@example.com", "date": str(d), "time": slots[0],
        "event_type": "Matrimonio", "consent": True}
check("prenotazione senza CSRF rifiutata", c.post("/api/appuntamento", json=body).status_code == 400)
r = c.post("/api/appuntamento", json=body, headers=H)
check("prenotazione ok", r.status_code == 200, r.get_data(as_text=True))
check("slot occupato sparisce", slots[0] not in c.get(f"/api/slots?date={d}").get_json())
check("doppia prenotazione rifiutata", c.post("/api/appuntamento", json=body, headers=H).status_code == 409)
check("senza consenso rifiutata", c.post("/api/appuntamento", json={**body, "consent": False}, headers=H).status_code == 400)
token = r.get_json()["token"]
check("pagina gestione", "Il tuo appuntamento" in c.get(f"/appuntamento/{token}").get_data(as_text=True))
r = c.post(f"/appuntamento/{token}", data={"csrf": tok, "act": "annulla"})
check("annullamento", "annullato" in r.get_data(as_text=True))

# preventivo
qt = {"name": "Prev", "phone": "3330001111", "email": "p@example.com", "event_type": "Festa privata", "event_date": str(d),
      "place": "Napoli", "guests": "100", "services": ["Audio", "Luci"], "consent": True}
check("preventivo ok", c.post("/api/preventivo", json=qt, headers=H).status_code == 200)

# chat
r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "Vorrei prenotare un appuntamento"}]}, headers=H)
check("chat prenota", r.status_code == 200 and r.get_json()["action"] == "prenota", r.get_data(as_text=True))
r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "quanto costa la luna?"}]}, headers=H)
check("chat preventivo senza prezzi inventati", "Non pubblichiamo prezzi" in r.get_json()["reply"])

# admin
check("admin protetto", c.get("/admin/").status_code == 302)
check("upload anonimo bloccato", c.post("/admin/foto/upload").status_code == 302)
lg = c.get("/admin/login").get_data(as_text=True)
check("login errato", "Credenziali errate" in c.post("/admin/login", data={"csrf": csrf(lg), "username": "admin", "password": "x"}).get_data(as_text=True))
r = c.post("/admin/login", data={"csrf": csrf(lg), "username": "admin", "password": PW})
check("login ok", r.status_code == 302 and c.get("/admin/").status_code == 200)
for p in ["richieste", "disponibilita", "foto", "testi", "m/clienti", "m/fornitori", "m/magazzino", "m/eventi", "m/prima-nota",
          "m/recensioni", "documenti", "chiamate"]:
    check(f"admin/{p}", c.get(f"/admin/{p}").status_code == 200)
adm = c.get("/admin/foto").get_data(as_text=True)
A = {"X-CSRF-Token": csrf(adm)}
FETCH = {**A, "X-Requested-With": "fetch"}

# upload foto (stile telefono: JPEG con EXIF orientamento)
buf = io.BytesIO()
im = Image.new("RGB", (900, 600), (200, 20, 20))
ex = im.getexif()
ex[274] = 6
im.save(buf, "JPEG", exif=ex)
buf.seek(0)
r = c.post("/admin/foto/upload", data={"files": [(buf, "telefono.jpg")], "category": "Luci"},
           headers=FETCH, content_type="multipart/form-data")
check("upload immagine", r.get_json()["ok"] == ["telefono.jpg"], r.get_data(as_text=True))
r = c.post("/admin/foto/upload", data={"files": [(io.BytesIO(b"MZ\x90\x00 evil"), "virus.exe")]},
           headers=FETCH, content_type="multipart/form-data")
check("exe rifiutato", r.get_json()["ok"] == [] and r.get_json()["errors"], r.get_data(as_text=True))
r = c.post("/admin/foto/upload", data={"files": [(io.BytesIO(b"non immagine"), "falso.jpg")]},
           headers=FETCH, content_type="multipart/form-data")
check("falso jpg rifiutato", r.get_json()["ok"] == [])
r = c.post("/admin/foto/upload", data={"files": [(io.BytesIO(b"x"), "a.jpg")]}, content_type="multipart/form-data")
check("upload senza CSRF rifiutato", r.status_code == 400)
home = c.get("/").get_data(as_text=True)
check("foto nuova in galleria", 'alt="telefono"' in home)
with app.app_context():
    row = q("SELECT id,filename FROM media WHERE title='telefono'", one=True)
    mid, fname = row["id"], row["filename"]
check("file servito", c.get(f"/media/{fname}_960.webp").status_code == 200)
check("traversal bloccato", c.get("/media/..%2f..%2fdata%2flmc.db").status_code == 404)
im2 = Image.open(io.BytesIO(c.get(f"/media/{fname}_960.webp").data))
check("EXIF ruotata (900x600 -> verticale)", im2.height > im2.width, im2.size)
c.post(f"/admin/foto/{mid}/elimina", data={"csrf": A["X-CSRF-Token"]})
check("elimina foto", 'alt="telefono"' not in c.get("/").get_data(as_text=True))

# gestionale + PDF
r = c.post("/admin/documenti", data={"csrf": A["X-CSRF-Token"], "kind": "preventivo", "client_id": "1",
                                     "items": "Impianto audio;1;350\nLuci;2;100"})
check("crea documento", r.status_code == 302)
pdf = c.get("/admin/documenti/1.pdf")
check("PDF generato", pdf.status_code == 200 and pdf.data[:4] == b"%PDF")
check("modifica testi", c.post("/admin/testi", data={"csrf": A["X-CSRF-Token"], "claim": "Nuovo claim di prova"}).status_code == 302
      and "Nuovo claim di prova" in c.get("/").get_data(as_text=True))
check("webhook telefono spento", c.post("/webhook/telefono", json={}).status_code == 404)
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
