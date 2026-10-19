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
