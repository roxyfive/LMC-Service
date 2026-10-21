"""Contenuti della home: slide hero, foto delle skill, galleria, passi dell'intro.

Le foto arrivano sempre da foto/organizzate/ (tabella `media`, vedi foto_sync.py): quando le foto demo
vengono sostituite la home si aggiorna da sola. I testi sotto sono BOZZE descrittive e generiche
(nessun numero, cliente o premio): da far confermare al titolare.
"""
import json
import random
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

# (skill della foto, didascalia, sottotitolo): solo testo animato, niente voce sintetica.
# BOZZE generiche da far confermare al titolare (nessun numero, cliente o premio inventato).
INTRO_STEPS = [
    ("hero", "Napoli · Dal 16 febbraio 2025", "La Music Company Service"),
    ("allestimenti", "Il lato tecnico del tuo evento", "Progettazione e allestimenti"),
    ("audio", "Audio", "L'impianto giusto per ogni sala"),
    ("ledwall", "Ledwall e luci", "Il palco prende vita"),
    ("videosorveglianza", "Videosorveglianza", "Telecamere per eventi, locali e aziende"),
    ("eventi", "Eventi in tutta Italia", "Matrimoni, eventi privati, live e congressi"),
    ("hero", "Il tuo evento, sotto i riflettori", "Prenota un appuntamento o chiedi un preventivo"),
]

# Tema fotografico di ogni slide dell'intro (stesso ordine di INTRO_STEPS): parole chiave della foto più coerente e cartelle preferite.
# Ogni foto compare in UNA sola slide; senza una foto pertinente si ripiega su una qualsiasi non ancora usata (mai su una già mostrata).
INTRO_THEMES = [
    (r"cortile storico|allestimento audio", ("hero",)),
    (r"palco allestito|montaggio|struttur|allestit|rigging", ("installazioni", "galleria")),
    (r"mixer|regia audio|fonico|microfon|cassa", ("installazioni", "galleria")),
    (r"barre led|riflettor|proiettor|mirror|giochi di luce|luci", ("installazioni", "galleria")),
    (r"regia video|collegament|controlli|regia", ("galleria", "installazioni")),
    (r"teatro|prove|serata|pubblico|quinte", ("galleria", "hero")),
    (r"pomeriggio|riflettori d.atmosfera|facciata|prove luci|palco in cortile", ("hero",)),
]

# Numeri della sezione "In cifre": DEMO finché il titolare non fornisce quelli veri (settings.stats = JSON [{label,value,suffix}]).
# "24 ore" invece è reale (dati del cliente: aperto 24 ore).
STATS_DEMO = [("Eventi realizzati", 150, "+", True), ("Impianti attivi", 24, "", True), ("Aperti 24 ore su 24", 24, " h", False)]

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


def pick_skill_photos(images, fallback=False):
    """Una foto per skill: per parola chiave (foto non ancora usate), poi riuso della stessa. Senza una foto pertinente
    la skill resta SENZA foto (solo icona e testo): meglio niente che una foto che non c'entra. Con fallback=True
    (solo per le slide dell'intro, che hanno bisogno di uno sfondo) si ripiega su una foto qualsiasi non ancora usata."""
    pref = {"installazioni": 0, "galleria": 1, "hero": 2, "": 3}
    pool = sorted(images, key=lambda m: pref.get(folder_of(m), 3))
    cand = {slug: [m for m in pool if re.search(kw, _text(m))] for slug, _n, _t, kw in SKILLS}
    used, out = set(), {}
    # prima le skill con meno foto candidate, così non se le rubano a vicenda
    for slug in sorted(cand, key=lambda k: len(cand[k])):
        hits = cand[slug]
        pick = next((m for m in hits if m["id"] not in used), None) or (hits[0] if hits else None)
        if not pick and fallback:
            pick = next((m for m in pool if m["id"] not in used), None) or (pool[0] if pool else None)
        if pick:
            used.add(pick["id"])
            out[slug] = pick
    return out


def pick_intro_photos(pool, rng=None):
    """Una foto DIVERSA per ogni slide dell'intro (nessuna ripetizione), abbinata per tema alla didascalia. Ritorna una lista
    lunga quanto le slide che si riescono a coprire: se le foto non bastano le slide si riducono invece di ripetere."""
    rng = rng or random.Random()           # a ogni visita l'intro mescola le foto pertinenti: non mostra sempre le stesse
    pool = list(pool)
    rng.shuffle(pool)
    n = min(len(INTRO_STEPS), len(pool))
    cand = []
    for i in range(n):
        rx, folders = INTRO_THEMES[i] if i < len(INTRO_THEMES) else ("", ())
        rank = lambda m: (folders.index(folder_of(m)) if folder_of(m) in folders else len(folders))
        hits = sorted([m for m in pool if rx and re.search(rx, _text(m))], key=rank)
        cand.append(hits)
    used, out = set(), [None] * n
    for i in sorted(range(n), key=lambda k: len(cand[k])):      # prima le slide con meno scelta
        pick = next((m for m in cand[i] if m["id"] not in used), None)
        if pick:
            used.add(pick["id"]); out[i] = pick
    for i in range(n):                                          # le slide rimaste: foto non usata, preferibilmente della cartella giusta
        if out[i] is None:
            folders = INTRO_THEMES[i][1] if i < len(INTRO_THEMES) else ()
            free = [m for m in pool if m["id"] not in used]
            free.sort(key=lambda m: (folders.index(folder_of(m)) if folder_of(m) in folders else len(folders)))
            if free:
                used.add(free[0]["id"]); out[i] = free[0]
    return out


def build(media):
    imgs = [m for m in media if m["kind"] == "image"]
    real = [m for m in imgs if not m["placeholder"]]
    pool = real or imgs
    by = lambda f: [m for m in pool if folder_of(m) == f]
    # hero della home: in evidenza, cartella hero, galleria, altre foto caricate dall'admin
    others = [m for m in pool if folder_of(m) not in ("hero", "galleria", "installazioni") and m["show_home"]]
    heroes = _uniq([m for m in pool if m["featured"] and folder_of(m) == "hero"] + by("hero"))
    # con almeno 3 foto nella cartella hero la slideshow usa SOLO quelle (panoramiche scelte); altrimenti si completa con galleria e altre
    hero_slides = heroes[:6] if len(heroes) >= 3 else (_uniq([m for m in pool if m["featured"]] + by("hero") + by("galleria") + others)[:6] or pool[:6])
    photos = pick_skill_photos(pool)                      # per le card delle skill: solo foto pertinenti
    skills = [dict(slug=s, nome=n, testo=t, img=(photos[s]["filename"] if s in photos else None),
                   alt=(photos[s]["title"] if s in photos else n)) for s, n, t, _k in SKILLS]
    intro_photos = pick_intro_photos(pool)               # slide dell'intro: una foto diversa per slide, mai ripetuta
    steps = [dict(cap=cap, sub=sub, img=f"/media/{m['filename']}_1600.webp")
             for (sk, cap, sub), m in zip(INTRO_STEPS, intro_photos) if m]
    media_dir = Path(ROOT) / "app" / "static" / "media"
    cues = []
    try:   # voce.json: inizio (in secondi) di ogni slide, ricavato dalle pause della voce
        cues = [float(x) for x in json.loads((media_dir / "voce.json").read_text(encoding="utf-8"))["cues"]]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if len(cues) != len(steps):
        cues = []
    return dict(hero_slides=hero_slides, skills=skills, skill_ids={m["id"] for m in photos.values()}, real_photos=bool(real), intro_steps=steps, voce_cues=cues,
                voce_url="/static/media/voce.mp3" if (media_dir / "voce.mp3").is_file() else "")


def stats(settings, demo):
    """Lista numeri da mostrare: reali da settings.stats, altrimenti quelli DEMO (solo in modalità demo)."""
    try:
        real = json.loads(settings.get("stats", "") or "[]")
        out = [dict(label=str(x["label"])[:40], value=int(x["value"]), suffix=str(x.get("suffix", ""))[:6], demo=False) for x in real]
        if out:
            return out
    except (ValueError, KeyError, TypeError):
        pass
    if not demo:
        return [dict(label=l, value=v, suffix=sf, demo=False) for l, v, sf, d in STATS_DEMO if not d]
    return [dict(label=l, value=v, suffix=sf, demo=d) for l, v, sf, d in STATS_DEMO]
