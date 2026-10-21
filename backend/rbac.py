"""Ruoli e permessi dell'admin + registro delle attività.

Due ruoli:
  · admin          il titolare: accede a TUTTO.
  · collaboratore  agenda, richieste, galleria (solo caricamento), materiale/eventi (check-list) e assistente.
                   NON vede fatture, acconti, statistiche, tariffe, impostazioni, testi, clienti, utenti, registro.

Sicurezza «di default negata»: ogni pagina dell'admin è riservata all'amministratore SALVO quelle elencate in COLLAB_OK.
Una pagina nuova, dimenticata nell'elenco, resta quindi chiusa al collaboratore (e il test dei permessi la controlla).
"""
import re
from flask import request, session, g, redirect, url_for, render_template
from .db import ex, q
from .security import current_user

ADMIN, COLLAB = "admin", "collaboratore"
ROLES = {ADMIN: "Amministratore (titolare)", COLLAB: "Collaboratore"}

# endpoint del blueprint "admin" consentiti al collaboratore (nome della funzione, senza il prefisso "admin.")
COLLAB_OK = {
    "dashboard", "agenda", "agenda_azione", "agenda_nota",
    "richieste", "app_stato", "quote_stato", "wa_riepilogo",
    "foto", "foto_upload", "foto_update", "foto_reorder",
    "mod_list", "mod_edit", "event_equipment", "chiamate",
    "password", "logout", "login",
}
COLLAB_MODS = {"magazzino", "eventi"}          # moduli generici (/admin/m/<mod>) aperti al collaboratore
COLLAB_NO_DELETE = True                        # il collaboratore non elimina nulla (nemmeno in magazzino/eventi)

# voci del menu laterale: (sezione, etichetta, url, endpoint di riferimento, icona, solo_admin)
MENU = [
    ("Gestione", "Dashboard", "/admin/", "dashboard", "home"),
    ("Gestione", "Agenda", "/admin/agenda", "agenda", "calendar"),
    ("Gestione", "Richieste", "/admin/richieste", "richieste", "inbox"),
    ("Gestione", "Preventivi", "/admin/documenti", "documenti", "file"),
    ("Gestione", "Fatture", "/admin/fatture", "fatture", "receipt"),
    ("Gestione", "Acconti", "/admin/acconti", "acconti", "euro"),
    ("Gestione", "Clienti", "/admin/m/clienti", "mod_list:clienti", "users"),
    ("Contenuti", "Galleria", "/admin/foto", "foto", "image"),
    ("Contenuti", "Recensioni", "/admin/recensioni", "recensioni", "star"),
    ("Contenuti", "Testi del sito", "/admin/testi", "testi", "edit"),
    ("Contenuti", "Tariffe", "/admin/tariffe", "tariffe", "tag"),
    ("Operativo", "Materiale", "/admin/m/magazzino", "mod_list:magazzino", "box"),
    ("Operativo", "Eventi", "/admin/m/eventi", "mod_list:eventi", "mic"),
    ("Operativo", "Assistente e chat", "/admin/chiamate", "chiamate", "chat"),
    ("Operativo", "WhatsApp", "/admin/whatsapp", "whatsapp", "wa"),
    ("Analisi", "Statistiche", "/admin/statistiche", "statistiche", "chart"),
    ("Analisi", "Report e visite", "/admin/report", "report", "pulse"),
    ("Sistema", "Team e contatti", "/admin/m/team", "mod_list:team", "team"),
    ("Sistema", "Utenti e permessi", "/admin/utenti", "utenti", "shield"),
    ("Sistema", "Registro attività", "/admin/registro", "registro", "log"),
    ("Sistema", "Impostazioni", "/admin/impostazioni", "impostazioni", "gear"),
    ("Sistema", "Backup", "/admin/backup", "backup", "db"),
]


def role_of(u=None):
    u = u or current_user()
    return (u["role"] if u else "") or ADMIN


def is_admin(u=None):
    return role_of(u) == ADMIN


def allowed(role, ep, view_args=None, method="GET"):
    if role == ADMIN:
        return True
    if role != COLLAB or ep not in COLLAB_OK:
        return False
    va = view_args or {}
    if ep in ("mod_list", "mod_edit"):
        return va.get("mod") in COLLAB_MODS
    if ep == "event_equipment":
        return True
    return True


def menu_for(role):
    out, seen = [], {}
    for sec, label, url, ref, icon in MENU:
        ep, _, mod = ref.partition(":")
        ok = allowed(role, ep, {"mod": mod} if mod else {})
        if not ok:
            continue
        if sec not in seen:
            seen[sec] = []
            out.append((sec, seen[sec]))
        seen[sec].append(dict(label=label, url=url, icon=icon))
    return out


# ------------------------------------------------------------------ registro attività
_SECRET_KEYS = re.compile(r"pass|pw|token|secret|key|^old$|^new|^csrf$", re.I)

FRIENDLY = {
    "login": "Accesso", "logout": "Uscita", "password": "Cambio password", "utenti": "Utenti", "utente_crea": "Utente creato",
    "utente_modifica": "Utente modificato", "utente_attiva": "Utente attivato/disattivato", "utente_reset": "Password utente azzerata",
    "fattura_salva": "Fattura salvata", "fattura_emetti": "Fattura emessa", "fattura_stato": "Stato fattura", "fattura_elimina": "Fattura eliminata",
    "fattura_sdi": "Stato SDI fattura", "fatture_impostazioni": "Impostazioni fatturazione", "fattura_da": "Fattura creata da pratica",
    "acconto_nuovo": "Acconto registrato", "acconto_elimina": "Acconto eliminato", "tariffa_salva": "Tariffa salvata", "tariffa_elimina": "Tariffa eliminata",
    "impostazioni_salva": "Impostazioni modificate", "testi": "Testi del sito modificati", "foto_upload": "Foto caricate", "foto_update": "Foto modificata",
    "foto_delete": "Foto eliminata", "foto_publish": "Foto pubblicata/nascosta", "foto_sync": "Sincronizzazione foto",
    "app_stato": "Stato appuntamento", "quote_stato": "Stato richiesta preventivo", "agenda_azione": "Agenda: azione sul giorno",
    "recensione_richiedi": "Richiesta recensione", "recensione_stato": "Recensione approvata/rifiutata", "recensione_elimina": "Recensione eliminata",
    "wa_riepilogo": "Riepilogo WhatsApp inviato", "documento_del": "Preventivo eliminato", "documento_stato": "Stato preventivo",
    "mod_list": "Voce aggiunta", "mod_edit": "Voce modificata", "mod_del": "Voce eliminata", "report_invia": "Report inviato",
}


def audit(action, detail="", user=None):
    u = user or current_user()
    try:
        ex("INSERT INTO audit_log(user_id,username,role,action,detail,ip) VALUES(?,?,?,?,?,?)",
           (u["id"] if u else None, (u["username"] if u else "")[:60], (u["role"] if u else "")[:20] or "", action[:80], detail[:500],
            (request.remote_addr or "")[:45] if request else ""))
    except Exception:
        pass


def _form_summary():
    parts = []
    for k, v in request.form.items():
        if k == "csrf" or _SECRET_KEYS.search(k):
            continue
        v = (v or "").strip()
        if v:
            parts.append(f"{k}={v[:50]}")
    return "; ".join(parts)[:300]


def install(bp):
    """Collega ai blueprint dell'admin: controllo dei permessi, cambio password obbligatorio e registro delle azioni."""

    @bp.before_request
    def gate():
        ep = (request.endpoint or "").split(".", 1)[-1]
        if ep in ("login", "static", ""):
            return None
        u = current_user()
        if not u:
            return redirect(url_for("admin.login"))
        if u["must_change"] and ep not in ("password", "logout"):
            return redirect(url_for("admin.password"))
        if allowed(role_of(u), ep, request.view_args, request.method):
            return None
        audit("Accesso negato", f"{request.method} {request.path}")
        return render_template("admin/negato.html"), 403

    @bp.after_request
    def log_actions(resp):
        try:
            if request.method == "POST" and resp.status_code < 400 and request.endpoint and request.endpoint.startswith("admin."):
                ep = request.endpoint.split(".", 1)[1]
                if ep in ("login", "foto_reorder"):
                    return resp
                label = FRIENDLY.get(ep, ep.replace("_", " "))
                if ep in ("mod_list", "mod_edit", "mod_del"):
                    label = f"{label} ({(request.view_args or {}).get('mod', '')})"
                audit(label, f"{request.path} · {_form_summary()}")
        except Exception:
            pass
        return resp
