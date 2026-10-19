"""Avvio locale: `python run.py` (oppure doppio clic su avvia.bat)."""
import sys
from backend import create_app
from backend.config import PORT, MODE

app = create_app()

if __name__ == "__main__":
    if "--promemoria" in sys.argv:
        from backend import reminders_once
        with app.app_context():
            reminders_once()
        print("Promemoria inviati")
    else:
        print(f"LMC Service [{MODE.upper()}] -> http://localhost:{PORT}  | admin: http://localhost:{PORT}/admin")
        app.run(host="127.0.0.1", port=PORT, debug=False)
