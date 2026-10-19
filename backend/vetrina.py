"""Contenuti della home: slide hero, foto delle skill, galleria, passi dell'intro.

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
    for i, (sk, cap, sub) in enumerate(INTRO_STEPS):
        m = photos.get(sk) if sk != "hero" else (hero_pool[(i // 6) % len(hero_pool)] if hero_pool else None)
        steps.append(dict(cap=cap, sub=sub, img=f"/media/{m['filename']}_1600.webp" if m else ""))
    media_dir = Path(ROOT) / "app" / "static" / "media"
    cues = []
    try:   # voce.json: inizio (in secondi) di ogni slide, ricavato dalle pause della voce
        cues = [float(x) for x in json.loads((media_dir / "voce.json").read_text(encoding="utf-8"))["cues"]]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if len(cues) != len(steps):
        cues = []
    return dict(hero_slides=hero_slides, skills=skills, intro_steps=steps, voce_cues=cues,
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
