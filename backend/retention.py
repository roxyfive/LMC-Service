"""Conservazione dei dati personali (GDPR: limitazione della conservazione). Eseguita ogni ora dallo sfondo del sito.

 · richieste di preventivo e appuntamenti: dopo N mesi (default 24, setting «retention_mesi») i dati personali diventano anonimi
   (le righe restano per le statistiche e per i riferimenti di fatture e agenda);
 · chiamate/riepiloghi dell'assistente e registro WhatsApp: 12 mesi; conteggi anonimi delle visite: 26 mesi;
 · email usata solo per inviare il link della recensione: cancellata appena la recensione è inviata o dopo 60 giorni senza risposta.
Fatture, clienti fatturati e registro attività NON sono toccati (obblighi fiscali e di sicurezza).
"""
from .db import get_db, get_setting

ANON = "(anonimizzato)"
MESI_LOG = 12
MESI_STAT = 26


def mesi():
    try:
        return max(6, min(120, int(get_setting("retention_mesi", "24") or 24)))
    except ValueError:
        return 24


def _do(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.rowcount


def run():
    """Ritorna un dizionario con quante righe sono state toccate per ciascun tipo (utile ai test e al registro)."""
    n = mesi()
    lim = f"-{n} months"
    out = {}
    out["richieste"] = _do("UPDATE quotes SET name=?, phone='', email='', place='', notes='' WHERE created < datetime('now',?) AND name != ?", (ANON, lim, ANON))
    out["appuntamenti"] = _do("UPDATE appointments SET name=?, phone='', email='', notes='', admin_note='' WHERE created < datetime('now',?) AND name != ?", (ANON, lim, ANON))
    out["chiamate"] = _do("DELETE FROM calls WHERE created < datetime('now',?)", (f"-{MESI_LOG} months",))
    out["whatsapp"] = _do("DELETE FROM wa_log WHERE ts < datetime('now',?)", (f"-{MESI_LOG} months",))
    out["visite"] = _do("DELETE FROM stats_events WHERE ts < datetime('now',?)", (f"-{MESI_STAT} months",))
    out["email_recensioni"] = _do("UPDATE reviews SET email='' WHERE email != '' AND (status != 'richiesta' OR requested_at < datetime('now','-60 days'))")
    return out
