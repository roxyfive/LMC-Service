"""Contenuti della home animata: slide hero, foto delle skill, passi dell'intro cinematografica.

Le foto arrivano sempre da foto/organizzate/ (tabella `media`, vedi foto_sync.py): quando le foto demo
vengono sostituite la home si aggiorna da sola. I testi sotto sono BOZZE descrittive e generiche
(nessun numero, cliente o premio): da far confermare al titolare.
"""
import json
import re
from pathlib import Path
from .config import FOTO_DIR, ROOT

# slug, nome, testo, parole chiave che nel nome file/didascalia indicano la foto giusta
SKILLS = [
    ("videosorveglianza", "Videosorveglianza", "Impianti di telecamere per tenere sotto controllo eventi, locali e spazi aziendali.",
     r"telecamer|sorveglianz|cctv|dome|videocamer|security"),
    ("ledwall", "Ledwall", "Pareti LED per palchi, fondali e contenuti video che catturano il pubblico.",
     r"ledwall|led wall|videowall|maxischermo|schermo"),
    ("audio", "Audio", "Impianti audio per eventi, meeting e show, dimensionati sulla sala e sul pubblico.",
     r"audio|casse|line ?array|mixer|regia|fonico|microfon|subwoofer"),
    ("allestimenti", "Allestimenti", "Palchi, strutture e allestimenti tecnici su misura, dalla progettazione alla serata.",
     r"allestiment|palco|struttur|truss|montaggio|rigging"),
    ("eventi", "Eventi", "Matrimoni, eventi privati, live e congressi: il lato tecnico, in tutta Italia.",
     r"concert|event|festa|matrimon|serata|pubblico|live|show"),
]

# (skill della foto, didascalia, sottotitolo, testo della voce narrante)
INTRO_STEPS = [
    ("hero", "Napoli · Dal 16 febbraio 2025", "La Music Company Service",
     "Benvenuti in La Music Company Service. Siamo a Napoli e lavoriamo in tutta Italia."),
    ("allestimenti", "Il lato tecnico del tuo evento", "Progettazione e allestimenti",
     "Progettiamo e realizziamo la parte tecnica dei vostri eventi, dal palco al meeting."),
    ("audio", "Audio", "L'impianto giusto per ogni sala",
     "Impianti audio pensati per la sala e per il pubblico, perché ogni parola e ogni nota arrivino chiare."),
    ("ledwall", "Ledwall e luci", "Il palco prende vita",
     "Ledwall e luci trasformano un palco in uno spettacolo."),
    ("videosorveglianza", "Videosorveglianza", "Telecamere per eventi, locali e aziende",
     "E se serve, installiamo impianti di videosorveglianza per tenere sotto controllo spazi ed eventi."),
    ("eventi", "Eventi in tutta Italia", "Matrimoni, live, congressi",
     "Matrimoni, feste private, concerti e congressi: ovunque ci sia un evento, noi portiamo la tecnica."),
    ("hero", "Il tuo evento, sotto i riflettori", "Prenota un appuntamento o chiedi un preventivo",
     "Raccontateci il vostro evento: prenotate un appuntamento o richiedete un preventivo. Vi aspettiamo."),
]

_man = {"mtime": None, "data": {}}


def _manifest():
    p = FOTO_DIR / "_manifest.json"
    try:
        mt = p.stat().st_mtime
        if _man["mtime"] != mt:
            _man.update(mtime=mt, data=json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        _man.update(mtime=None, data={})
    return _man["data"]


def folder_of(m):
    src = m["source"] or ""
    return src[len("cartella:"):].split("/")[0] if src.startswith("cartella:") else ""


def _text(m):
    src = m["source"] or ""
    key = src[len("cartella:"):].split("#")[0] if src.startswith("cartella:") else ""
    meta = _manifest().get(key, {})
    return f"{m['title']} {m['caption']} {meta.get('origine', '')} {key}".lower().replace("_", " ").replace("-", " ")


def _uniq(rows):
    seen, out = set(), []
    for m in rows:
        if m["id"] not in seen:
            seen.add(m["id"])
            out.append(m)
    return out


def pick_skill_photos(images):
    """Una foto per skill: prima per parola chiave (foto non ancora usate), poi per riuso, poi a rotazione."""
    pref = {"installazioni": 0, "galleria": 1, "hero": 2, "": 3}
    pool = sorted(images, key=lambda m: pref.get(folder_of(m), 3))
    cand = {slug: [m for m in pool if re.search(kw, _text(m))] for slug, _n, _t, kw in SKILLS}
    used, out = set(), {}
    # prima le skill con meno foto candidate, così non se le rubano a vicenda
    for slug in sorted(cand, key=lambda k: len(cand[k])):
        hits = cand[slug]
        pick = next((m for m in hits if m["id"] not in used), None) or (hits[0] if hits else None) \
            or next((m for m in pool if m["id"] not in used), None) or (pool[0] if pool else None)
        if pick:
            used.add(pick["id"])
            out[slug] = pick
    return out


def build(media):
    imgs = [m for m in media if m["kind"] == "image"]
    real = [m for m in imgs if not m["placeholder"]]
    pool = real or imgs
    by = lambda f: [m for m in pool if folder_of(m) == f]
    # hero della home: in evidenza, cartella hero, galleria, altre foto caricate dall'admin
    others = [m for m in pool if folder_of(m) not in ("hero", "galleria", "installazioni") and m["show_home"]]
    hero_slides = _uniq([m for m in pool if m["featured"]] + by("hero") + by("galleria") + others)[:6] or pool[:6]
    photos = pick_skill_photos(pool)
    skills = [dict(slug=s, nome=n, testo=t, img=(photos[s]["filename"] if s in photos else None),
                   alt=(photos[s]["title"] if s in photos else n)) for s, n, t, _k in SKILLS]
    hero_pool = _uniq(by("hero") + [m for m in pool if m["featured"]] + hero_slides)
    steps = []
    for i, (sk, cap, sub, voce) in enumerate(INTRO_STEPS):
        m = photos.get(sk) if sk != "hero" else (hero_pool[(i // 6) % len(hero_pool)] if hero_pool else None)
        steps.append(dict(cap=cap, sub=sub, voce=voce, img=f"/media/{m['filename']}_1600.webp" if m else ""))
    voce_file = Path(ROOT) / "app" / "static" / "media" / "voce.mp3"
    return dict(hero_slides=hero_slides, skills=skills, intro_steps=steps,
                voce_url="/static/media/voce.mp3" if voce_file.is_file() else "")
