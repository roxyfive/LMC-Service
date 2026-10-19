import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA = Path(os.getenv("DATA_DIR") or ROOT / "data")
UPLOADS = DATA / "uploads"
DB_PATH = DATA / "lmc.db"
MODE = os.getenv("APP_MODE", "demo").lower()
SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(24).hex()
PORT = int(os.getenv("PORT", "5000"))
MAX_IMG = 12 * 1024 * 1024
MAX_VID = 60 * 1024 * 1024
CATEGORIES = ["Eventi", "Installazioni", "Show Demo", "Audio", "Luci", "Video", "Progettazione", "Meeting"]
FOTO_DIR = Path(os.getenv("FOTO_DIR") or ROOT / "foto" / "organizzate")
