import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA = Path(os.getenv("DATA_DIR") or ROOT / "data")
UPLOADS = DATA / "uploads"
DB_PATH = DATA / "lmc.db"
MODE = os.getenv("APP_MODE", "demo").lower()


def _secret_key():
    """Chiave di sessione: da .env, altrimenti generata una volta e salvata in data/secret.key
    (così tutti i worker di gunicorn e i riavvii usano la stessa chiave: sessioni e CSRF restano validi)."""
    k = os.getenv("SECRET_KEY", "").strip()
    if k and not k.startswith("cambia-questa"):
        return k
    f = DATA / "secret.key"
    try:
        if f.exists():
            return f.read_text().strip()
        DATA.mkdir(parents=True, exist_ok=True)
        k = os.urandom(32).hex()
        f.write_text(k)
        try:
            f.chmod(0o600)
        except OSError:
            pass
        return k
    except OSError:
        return os.urandom(32).hex()


SECRET_KEY = _secret_key()
PORT = int(os.getenv("PORT", "5000"))
MAX_IMG = 12 * 1024 * 1024
MAX_VID = 60 * 1024 * 1024
CATEGORIES = ["Eventi", "Installazioni", "Show Demo", "Audio", "Luci", "Video", "Progettazione", "Meeting"]
FOTO_DIR = Path(os.getenv("FOTO_DIR") or ROOT / "foto" / "organizzate")


def production_warnings():
    """Controlli di buon senso all'avvio in produzione (stampati nel log: journalctl -u lmc)."""
    if MODE != "production":
        return []
    w = []
    if os.getenv("COOKIE_SECURE") != "1":
        w.append("COOKIE_SECURE=1 mancante: dietro HTTPS i cookie di sessione devono essere 'secure'.")
    if os.getenv("TRUST_PROXY") != "1":
        w.append("TRUST_PROXY=1 mancante: dietro nginx IP reale e rate limit non funzionano correttamente.")
    if os.getenv("ADMIN_PASSWORD"):
        w.append("ADMIN_PASSWORD è ancora nel .env: dopo il primo avvio cancellala (la password si cambia da Admin > Password).")
    if not os.getenv("SECRET_KEY") and not (DATA / "secret.key").exists():
        w.append("SECRET_KEY non impostata: ne verrà generata una e salvata in data/secret.key (ok, ma includila nei backup).")
    return w
