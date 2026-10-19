import os
import json
import urllib.request
from datetime import date, timedelta
from .db import all_settings

SYSTEM = ("Sei l'assistente virtuale di LMC Service. Rispondi SEMPRE in italiano, breve e cordiale. "
          "Usa SOLO le informazioni seguenti. Se non sai o manca un dato (es. prezzi, telefono), "
          "dillo e indirizza al contatto umano o al modulo preventivo. Non inventare mai nulla. "
          "Per prenotare invita a usare il pulsante 'Prenota' del sito. Se chiedono numeri, email o persone, usa i dati di 'Contatti e team' senza modificarli. Tono professionale e cordiale, frasi brevi.\n\nINFORMAZIONI:\n")


def _servizi(s):
    try:
        return json.loads(s.get("servizi", "[]") or "[]")
    except ValueError:
        return []


def _team():
    from .db import q
    return q("SELECT * FROM team WHERE visible='si' ORDER BY sort, id")


def _real(v):
    return bool(v) and "[DA" not in v


def _person(m):
    bits = [m["name"] + (f" ({m['role']})" if m["role"] else "")]
    if _real(m["phone"]):
        bits.append(f"telefono/WhatsApp {m['phone']}")
    if _real(m["email"]):
        bits.append(f"email {m['email']}")
    if m["note"]:
        bits.append(m["note"])
    return ", ".join(bits)


def knowledge():
    s = all_settings()
    serv = "; ".join(f"{x['nome']}: {x['testo']}" for x in _servizi(s))
    team = "; ".join(_person(m) for m in _team()) or "nessun contatto inserito"
    return "\n".join([
        f"Azienda: {s.get('brand')} ({s.get('brand_short')}), {s.get('city')}. Titolare: {s.get('owner')}. Fondata il {s.get('founded')}.",
        f"Chi siamo: {s.get('chi_siamo')}",
        f"Servizi: {serv}",
        f"Zone coperte: {s.get('zone')}",
        f"Contatti e team: {team}",
        f"Telefono principale: {s.get('telefono') if _real(s.get('telefono')) else 'non indicato'} | Email: {s.get('email') if _real(s.get('email')) else 'non indicata'} | Orari: {s.get('orari') if _real(s.get('orari')) else 'non indicati'}",
        "Preventivo: si compila il modulo 'Richiedi preventivo' (tipo evento, data, luogo, ospiti, servizi); il titolare risponde. Nessun prezzo è pubblicato.",
        "Appuntamento: si sceglie giorno e ora nel calendario del sito; arriva conferma via email e si può modificare o annullare dal link ricevuto.",
    ])


def next_slots(n=3):
    from .public import free_slots
    out = []
    for i in range(1, 30):
        day = (date.today() + timedelta(days=i)).isoformat()
        for t in free_slots(day)[:2]:
            out.append(f"{day} {t}")
        if len(out) >= n:
            break
    return out[:n]


def _has(t, *keys):
    return any(k in t for k in keys)


def fallback(text):
    """Risposte dai dati del database (impostazioni + team), senza servizi esterni."""
    t = text.lower()
    s = all_settings()
    team = list(_team())
    tel = s.get("telefono") if _real(s.get("telefono")) else ""
    orari = s.get("orari") if _real(s.get("orari")) else ""
    # una persona del team citata per nome o ruolo
    for m in team:
        if m["name"].lower().split()[0] in t or (m["role"] and m["role"].lower() in t):
            wants_phone = _has(t, "numero", "telefon", "cellulare", "chiam", "whatsapp", "contatt", "recapit", "sentire")
            if wants_phone or _has(t, "email", "mail"):
                parts = []
                if _real(m["phone"]):
                    parts.append(f"telefono/WhatsApp {m['phone']}")
                if _real(m["email"]):
                    parts.append(f"email {m['email']}")
                if parts:
                    extra = f" {m['note']}." if m["note"] else ""
                    return (f"Puoi contattare {m['name']}" + (f" ({m['role'].lower()})" if m["role"] else "") + ": " + ", ".join(parts) + "." + extra, None)
            return (f"{_person(m)}.", None)
    if _has(t, "prenot", "appuntament", "dispon", "quando posso"):
        sl = next_slots(3)
        return ("Puoi prenotare dal calendario del sito. Prossimi orari liberi: "
                + (", ".join(sl) if sl else "nessuno al momento, scrivici o chiamaci") + ". Premi 'Prenota ora'.", "prenota")
    if _has(t, "preventiv", "prezz", "costo", "quanto", "tariff", "listino"):
        return ("Per un preventivo compila il modulo 'Richiedi preventivo': evento, data, luogo, ospiti e servizi. Il titolare ti risponde. Non pubblichiamo prezzi fissi.", "preventivo")
    if _has(t, "numero", "telefon", "cellulare", "chiam", "whatsapp", "contatt", "recapit", "email", "mail", "parlare con"):
        lines = [_person(m) for m in team]
        if not lines and tel:
            lines = [f"telefono/WhatsApp {tel}" + (f", {orari}" if orari else "")]
        if lines:
            return ("Ecco i nostri contatti: " + "; ".join(lines) + ".", None)
        return ("In questo momento non ho un recapito da darti: usa il modulo preventivo o il pulsante Prenota e ti ricontattiamo.", "preventivo")
    if _has(t, "orari", "orario", "aperto", "aperti", "apert", "24 ore", "quando siete", "disponibili"):
        if orari:
            return (f"{orari}." + (f" Per parlarci: {tel}." if tel else ""), None)
        return ("Gli orari non sono ancora indicati: scrivici dal modulo preventivo e ti rispondiamo.", None)
    if _has(t, "noleggi", "attrezzatur", "allestiment", "organizz", "eventi", "serviz", "audio", "luci", "luce", "video", "ledwall", "led", "videosorveglianza", "telecamer", "progett", "cosa fate", "fate", "offrite"):
        return ("Ci occupiamo di: " + "; ".join(f"{x['nome']}" for x in _servizi(s)) + ". Lavoriamo anche con audio, luci, video e ledwall. "
                f"Operiamo a {s.get('city')} e in tutta Italia. Vuoi un preventivo?", "preventivo")
    if _has(t, "dove", "zone", "italia", "napoli", "trasfert", "sede"):
        return (f"Siamo a {s.get('city')} e lavoriamo in tutta Italia.", None)
    if _has(t, "chi siete", "chi sei", "storia", "titolare", "nasc", "fondat"):
        return (s.get("chi_siamo", ""), None)
    if _has(t, "ciao", "buongiorno", "buonasera", "salve", "hey"):
        return ("Ciao! Sono l'assistente di LMC Service. Posso aiutarti con servizi, preventivi, appuntamenti e contatti.", None)
    if _has(t, "grazie"):
        return ("Prego, a disposizione! Se vuoi, posso aiutarti con un preventivo o un appuntamento.", None)
    return ("Non ho questa informazione. Posso aiutarti con servizi, preventivi, appuntamenti e contatti"
            + (f", oppure chiama {tel}." if tel else "."), None)


def chat(messages):
    last = messages[-1]["content"] if messages else ""
    base, key, model = os.getenv("AI_BASE_URL"), os.getenv("AI_API_KEY"), os.getenv("AI_MODEL")
    if base and key and model:
        try:
            body = json.dumps({"model": model, "max_tokens": 350, "messages":
                               [{"role": "system", "content": SYSTEM + knowledge()}] + messages[-10:]}).encode()
            req = urllib.request.Request(base.rstrip("/") + "/chat/completions", body,
                                         {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
            with urllib.request.urlopen(req, timeout=25) as r:
                txt = json.load(r)["choices"][0]["message"]["content"]
            lo = last.lower()
            action = "prenota" if ("prenot" in lo or "appuntament" in lo) else ("preventivo" if "preventiv" in lo else None)
            return txt, action
        except Exception:
            pass
    return fallback(last)
