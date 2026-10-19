"""Test footer SEGUICI: python -m tests.test_social"""
import os
import re
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="lmc_soc_")
os.environ["ADMIN_PASSWORD"] = "TestLocale123"
from backend import create_app

app = create_app()
c = app.test_client()
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok, fail = ok + bool(cond), fail + (not cond)


def csrf(html):
    return (re.search(r'name="csrf" content="([0-9a-f]+)"', html) or re.search(r'name="csrf" value="([0-9a-f]+)"', html)).group(1)


home = c.get("/").get_data(as_text=True)
check("Seguici presente con i default", 'aria-label="Seguici"' in home and "@lamusicompany.service" in home)
check("Rivedi l'intro ancora nel footer", "Rivedi l'intro" in home)
check("sito ufficiale nascosto senza URL", "Sito ufficiale" not in home)

lg = c.get("/admin/login").get_data(as_text=True)
c.post("/admin/login", data={"csrf": csrf(lg), "username": "admin", "password": "TestLocale123"})
page = c.get("/admin/testi").get_data(as_text=True)
check("campi social in Admin", 'name="sito_url"' in page and 'name="facebook_nome"' in page)
t = csrf(page)
form = {k: v for k, v in re.findall(r'name="([a-z_0-9]+)"[^>]*value="([^"]*)"', page)}
form.update({"csrf": t, "sito_url": "https://www.example.it", "facebook_nome": "Pagina Test", "instagram": "https://www.instagram.com/test.profilo/"})
c.post("/admin/testi", data=form)
home = c.get("/").get_data(as_text=True)
check("sito ufficiale + nome Facebook + handle da admin", "Sito ufficiale" in home and "https://www.example.it" in home and "Pagina Test" in home and "@test.profilo" in home)
form.update({"sito_url": "", "instagram": "", "facebook": "", "tiktok": ""})
c.post("/admin/testi", data=form)
home = c.get("/").get_data(as_text=True)
check("sezione nascosta senza link", 'aria-label="Seguici"' not in home and "Rivedi l'intro" in home)
home = c.get("/").get_data(as_text=True)
form.update({"instagram": "https://www.instagram.com/lamusicompanyservice/", "facebook": "https://www.facebook.com/x", "tiktok": "https://www.tiktok.com/@lmc"})
c.post("/admin/testi", data=form)
home = c.get("/").get_data(as_text=True)
check("ordine Instagram, Facebook, TikTok", 0 < home.index("<small>Instagram") < home.index("<small>Facebook") < home.index("<small>TikTok"))
check("handle completo in una riga con title", 'title="@lamusicompanyservice"' in home and 'class="soc-n"' in home)
form.update({"tiktok": ""})
c.post("/admin/testi", data=form)
check("TikTok nascosto se vuoto", "<small>TikTok" not in c.get("/").get_data(as_text=True))
print(f"\n{ok} ok, {fail} falliti")
raise SystemExit(1 if fail else 0)
