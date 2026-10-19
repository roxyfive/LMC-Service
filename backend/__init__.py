import os
import threading
import time
from datetime import date, timedelta
from flask import Flask, jsonify, request, abort
from . import config
from .db import close_db, init_db, q, ex
from .security import csrf_token
from .mailer import send_mail


def create_app():
    app = Flask(__name__, template_folder="../app/templates", static_folder="../app/static")
    app.config.update(SECRET_KEY=config.SECRET_KEY, MAX_CONTENT_LENGTH=200 * 1024 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    init_db()
    from .seed import seed
    seed()
    app.teardown_appcontext(close_db)
    from .foto_sync import sync as sync_foto
    with app.app_context():
        try:
            sync_foto()  # pubblica le foto/video nuove di foto/organizzate/
        except Exception as e:  # un file rovinato non deve impedire l'avvio
            print("Sincronizzazione foto non riuscita:", e)
    from .public import bp as pub
    from .admin import bp as adm
    app.register_blueprint(pub)
    app.register_blueprint(adm)
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.after_request
    def headers(r):
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["X-Frame-Options"] = "SAMEORIGIN"
        r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return r

    @app.route("/webhook/telefono", methods=["POST"])
    def webhook_telefono():
        # Predisposto: attivo solo con PHONE_AI_ENABLED=1 e token valido.
        tok = os.getenv("PHONE_WEBHOOK_TOKEN", "")
        if os.getenv("PHONE_AI_ENABLED") != "1" or not tok or request.headers.get("X-Webhook-Token") != tok:
            abort(404)
        d = request.get_json(silent=True) or {}
        ex("INSERT INTO calls(from_number,transcript,payload) VALUES(?,?,?)",
           (str(d.get("from", ""))[:40], str(d.get("transcript", ""))[:8000], str(d)[:8000]))
        return jsonify(ok=True)

    @app.errorhandler(404)
    def nf(_e):
        return "Pagina non trovata", 404

    threading.Thread(target=_reminders, args=(app,), daemon=True).start()
    return app


def reminders_once():
    """Promemoria al cliente per gli appuntamenti confermati di domani."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    for a in q("SELECT * FROM appointments WHERE slot_date=? AND status='confermato' AND reminded=0", (tomorrow,)):
        send_mail(a["email"], "Promemoria appuntamento – LMC Service",
                  f"Ciao {a['name']}, ti ricordiamo l'appuntamento di domani {a['slot_date']} alle {a['slot_time']}.\nLMC Service")
        ex("UPDATE appointments SET reminded=1 WHERE id=?", (a["id"],))


def _reminders(app):
    while True:
        try:
            with app.app_context():
                reminders_once()
        except Exception:
            pass
        time.sleep(3600)
