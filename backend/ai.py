import os
import json
import urllib.request
from datetime import date, timedelta
from .db import all_settings

SYSTEM = ("Sei l'assistente virtuale di LMC Service. Rispondi SEMPRE in italiano, breve e cordiale. "
          "Usa SOLO le informazioni seguenti. Se non sai o manca un dato (es. prezzi, telefono), "
          "dillo e indirizza al contatto umano o al modulo preventivo. Non inventare mai nulla. "
          "Per prenotare invita a usare il pulsante 'Prenota' del sito.\n\nINFORMAZIONI:\n")


def _servizi(s):
    try:
        return json.loads(s.get("servizi", "[]") or "[]")
    except ValueError:
        return []


def knowledge():
    s = all_settings()
    serv = "; ".join(f"{x['nome']}: {x['testo']}" for x in _servizi(s))
    return "\n".join([
        f"Azienda: {s.get('brand')} ({s.get('brand_short')}), {s.get('city')}. Titolare: {s.get('owner')}. Fondata il {s.get('founded')}.",
        f"Chi siamo: {s.get('chi_siamo')}",
        f"Servizi: {serv}",
        f"Zone coperte: {s.get('zone')}",
        f"Telefono: {s.get('telefono')} | Email: {s.get('email')} | Orari: {s.get('orari')}",
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


def fallback(text):
    t = text.lower()
    s = all_settings()
    if any(k in t for k in ("prenot", "appuntament", "dispon", "quando")):
        sl = next_slots(3)
        return ("Puoi prenotare dal calendario del sito. Prossimi orari liberi: "
                + (", ".join(sl) if sl else "nessuno al momento, scrivici") + ". Premi 'Prenota ora'.", "prenota")
    if any(k in t for k in ("preventiv", "prezz", "costo", "quanto")):
        return ("Per un preventivo compila il modulo 'Richiedi preventivo': evento, data, luogo, ospiti e servizi. Il titolare ti risponde. Non pubblichiamo prezzi fissi.", "preventivo")
    if any(k in t for k in ("serviz", "audio", "luci", "video", "progett", "cosa fate", "fate")):
        return ("Offriamo: " + ", ".join(x["nome"] for x in _servizi(s)) + ". Eventi in tutta Italia.", None)
    if any(k in t for k in ("dove", "zone", "italia", "napoli", "trasfert")):
        return (f"Siamo a {s.get('city')} e lavoriamo in tutta Italia.", None)
    if any(k in t for k in ("chi siete", "chi sei", "storia", "titolare", "nasc")):
        return (s.get("chi_siamo", ""), None)
    if any(k in t for k in ("telefon", "contatt", "email", "whatsapp", "chiam")):
        return (f"Contatti: tel {s.get('telefono')}, email {s.get('email')}.", None)
    return ("Non ho questa informazione. Contatta il titolare dalla sezione Contatti, oppure chiedimi di servizi, preventivi o appuntamenti.", None)


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
