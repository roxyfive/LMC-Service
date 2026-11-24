import sqlite3
from flask import g
from .config import DB_PATH, DATA, UPLOADS, ROOT


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.execute("PRAGMA busy_timeout=10000")
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db:
        db.close()


def q(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def ex(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def init_db():
    DATA.mkdir(exist_ok=True)
    UPLOADS.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript((ROOT / "backend" / "schema.sql").read_text(encoding="utf-8"))
    # migrazioni leggere per database già esistenti (CREATE IF NOT EXISTS non aggiunge colonne)
    cols = {r[1] for r in con.execute("PRAGMA table_info(team)")}
    for name, ddl in (("notify", "TEXT DEFAULT 'si'"), ("on_duty", "TEXT DEFAULT 'no'")):
        if name not in cols:
            con.execute(f"ALTER TABLE team ADD COLUMN {name} {ddl}")
    # colonne del gestionale (utenti e ruoli, anagrafica fiscale, recensioni, galleria eventi)
    for table, adds in (
        ("admin_users", {"role": "TEXT DEFAULT 'admin'", "active": "INTEGER DEFAULT 1", "name": "TEXT DEFAULT ''", "email": "TEXT DEFAULT ''",
                         "must_change": "INTEGER DEFAULT 0", "created": "TEXT", "last_login": "TEXT"}),
        ("clients", {"address": "TEXT DEFAULT ''", "piva": "TEXT DEFAULT ''", "cf": "TEXT DEFAULT ''", "sdi_code": "TEXT DEFAULT ''", "pec": "TEXT DEFAULT ''"}),
        ("media", {"event_type": "TEXT DEFAULT ''", "event_date": "TEXT DEFAULT ''", "event_id": "INTEGER", "invoice_id": "INTEGER", "uploaded_by": "TEXT DEFAULT ''"}),
        ("reviews", {"stars": "INTEGER DEFAULT 5", "event": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'approvata'", "token": "TEXT", "email": "TEXT DEFAULT ''",
                     "requested_at": "TEXT", "created": "TEXT", "ref_type": "TEXT DEFAULT ''", "ref_id": "INTEGER"}),
        ("events", {"event_type": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'confermato'"}),
        ("appointments", {"admin_note": "TEXT DEFAULT ''"}),
    ):
        have = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        for name, ddl in adds.items():
            if name not in have:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
    con.execute("UPDATE admin_users SET role='admin' WHERE role IS NULL OR role=''")
    con.execute("UPDATE admin_users SET active=1 WHERE active IS NULL")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_review_token ON reviews(token) WHERE token IS NOT NULL")
    try:   # impedisce la doppia prenotazione dello stesso orario (se esistono già duplicati storici, l'indice viene saltato)
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_slot ON appointments(slot_date, slot_time) WHERE status != 'annullato'")
    except sqlite3.DatabaseError:
        pass
    try:
        con.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        pass
    con.commit()
    con.close()


def get_setting(key, default=""):
    r = q("SELECT value FROM settings WHERE key=?", (key,), one=True)
    return r["value"] if r else default


def set_setting(key, value):
    ex("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def all_settings():
    return {r["key"]: r["value"] for r in q("SELECT key,value FROM settings")}


# Segreti (token e chiavi API): tabella separata, mai inclusa in all_settings() e quindi mai passata ai template.
def get_secret(key, default=""):
    r = q("SELECT value FROM secrets WHERE key=?", (key,), one=True)
    return r["value"] if r else default


def set_secret(key, value):
    if value:
        ex("INSERT INTO secrets(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    else:
        ex("DELETE FROM secrets WHERE key=?", (key,))
