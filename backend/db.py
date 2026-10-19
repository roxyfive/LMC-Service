import sqlite3
from flask import g
from .config import DB_PATH, DATA, UPLOADS, ROOT


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
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
    con.commit()
    con.close()


def get_setting(key, default=""):
    r = q("SELECT value FROM settings WHERE key=?", (key,), one=True)
    return r["value"] if r else default


def set_setting(key, value):
    ex("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def all_settings():
    return {r["key"]: r["value"] for r in q("SELECT key,value FROM settings")}
