"""Avvio locale: `python run.py` (oppure doppio clic su avvia.bat)."""
import sys
from backend import create_app
from backend.config import PORT, MODE

app = create_app()

if __name__ == "__main__":
    if "--report" in sys.argv:      # per cron: python run.py --report  (invia i report dovuti in questo momento)
        from backend import reports_once
        with app.app_context():
            for key, ok, detail in reports_once():
                print(key, "OK" if ok else "ERRORE", detail)
        print("Report controllati")
    elif "--promemoria" in sys.argv:
        from backend import reminders_once
        with app.app_context():
            reminders_once()
        print("Promemoria inviati")
    else:
        print(f"LMC Service [{MODE.upper()}] -> http://localhost:{PORT}  | admin: http://localhost:{PORT}/admin")
        app.run(host="127.0.0.1", port=PORT, debug=False)
