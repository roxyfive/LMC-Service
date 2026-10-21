import secrets
from functools import wraps
from flask import session, request, abort, redirect, url_for
from .db import q


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def check_csrf():
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf")
    if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
        abort(400, "CSRF non valido")


def current_user():
    """Utente admin collegato (riga di admin_users) oppure None. Si rilegge dal database a ogni richiesta:
    un utente disattivato o declassato perde subito i permessi, senza aspettare la scadenza della sessione."""
    cached = getattr(request, "_lmc_user", False)      # una sola lettura per richiesta (non in g: in un contesto globale durerebbe troppo)
    if cached is not False:
        return cached
    u = None
    uid = session.get("uid")
    if uid:
        u = q("SELECT * FROM admin_users WHERE id=? AND active=1", (uid,), one=True)
    elif session.get("admin"):      # sessioni create prima dell'introduzione dei ruoli
        u = q("SELECT * FROM admin_users WHERE username=? AND active=1", (session.get("admin"),), one=True)
        if u:
            session["uid"] = u["id"]
    request._lmc_user = u
    return u


def admin_required(f):
    """Serve un utente collegato (qualsiasi ruolo). I limiti per ruolo li applica rbac.gate() su ogni pagina dell'admin."""
    @wraps(f)
    def w(*a, **k):
        if not current_user():
            session.pop("uid", None)
            session.pop("admin", None)
            return redirect(url_for("admin.login"))
        if request.method in ("POST", "PUT", "DELETE"):
            check_csrf()
        return f(*a, **k)
    return w
