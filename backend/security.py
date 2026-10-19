import secrets
from functools import wraps
from flask import session, request, abort, redirect, url_for


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def check_csrf():
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf")
    if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
        abort(400, "CSRF non valido")


def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("admin"):
            return redirect(url_for("admin.login"))
        if request.method in ("POST", "PUT", "DELETE"):
            check_csrf()
        return f(*a, **k)
    return w
