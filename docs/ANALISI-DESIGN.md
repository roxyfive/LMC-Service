# Analisi del sito e redesign (ottobre 2026)

## 1. Analisi critica della versione precedente (tema scuro rosso/oro)
**Punti di forza**: struttura chiara (hero → chi siamo → servizi → eventi → prenota → contatti); PWA, moduli e assistente funzionanti;
foto che si aggiornano da `foto/organizzate/`; immagini webp in 3 misure con lazy-load; nessuna libreria esterna; skip-link e `prefers-reduced-motion` già presenti.

**Debolezze**
- *Palette*: ~95% della pagina nera, testi grigi piccoli su nero, foto "affogate" da overlay scuri. Stanca nelle sezioni lunghe e dà un tono "discoteca" poco adatto a matrimoni/congressi.
- *Intro*: 7 passi × 5,6 s = ~40 s prima di vedere il sito; canvas con 36 gradienti radiali ridisegnati a ogni frame (pesante sui telefoni); voce robotica del browser (qualità diversa su ogni dispositivo); l'audio parte solo con un clic.
- *Hero*: titolo di 4 righe con "a capo" casuali ("… Il / tuo evento …"), lead grigio poco leggibile, nessun CTA preventivo prioritario.
- *Contenuti incompleti in vista*: telefono, email, orari e recensioni mostravano `[DA INSERIRE …]` come testo pubblico; la sezione Contatti era sepolta dopo due moduli lunghi, senza CTA.
- *Ridondanze*: "Servizi" duplicava le nuove skill; icone emoji diverse su ogni sistema; mappa OpenStreetMap di tutta Napoli senza indirizzo (inutile, carica terze parti e pesa).
- *Galleria*: colonne CSS che riordinano la lettura (per colonna, non per riga), didascalie piccole, lightbox senza gestione del focus (non accessibile da tastiera/screen reader).
- *Mobile*: due moduli lunghi uno dopo l'altro; menu a 9 voci; chip e pulsanti ok ma tanta scrittura grigia.
- *Accessibilità*: grigi su nero al limite, il lightbox non intrappolava il focus, l'intro non aveva una vera uscita da tastiera (ora Esc).

**Cosa toglierebbe un esperto**: l'intro lunga e la voce sintetica, la sezione Servizi duplicata, le emoji, la mappa, i `[DA INSERIRE]` visibili, il canvas.

## 2. Ricerca web: cosa è stato possibile e cosa no
L'ambiente blocca l'accesso diretto ai siti. **Domini bloccati** (il browser/curl/WebFetch non li raggiungono):
`www.livenation.com`, `www.tomorrowland.com`, `www.ushuaiaibiza.com`, `www.stagetec.com`, `www.neg-earth.com`,
`www.pixelartlive.com`, `www.stufish.com`, `www.cameratawards.com`, `www.awwwards.com`, `www.pgl-proservice.it`.
Funzionano solo le ricerche web (riassunti, non le pagine reali): quindi **non ho potuto misurare palette, font e animazioni reali** di quei siti.
Quello che segue viene dai riassunti delle ricerche e da pratiche consolidate; va letto come orientamento, non come analisi dei singoli siti.

**Emerso dalla ricerca**
- Produzioni/festival: estetica *cinematografica* (immagini a tutto schermo, video/slide, tipografia grande e in movimento); siti di eventi di lusso: portfolio *editoriale* con gallerie "a storia", immagini ad alta qualità caricate in modo leggero.
- Service italiani di audio/luci/ledwall (PGL Pro Service, AVL Produzioni, RPS, AudioEntertainment…): presentano servizi per elenco concreto (ledwall in mq, potenza audio, strutture, palchi), zone coperte e contatto rapido; poche immagini curate.
- Linee guida ricorrenti (Awwwards, guide di kinetic typography): reveal allo scroll e titoli che compaiono parola/lettera, *ma* con prestazioni e `prefers-reduced-motion` rispettati; la usabilità pesa quanto l'estetica.
- Siti di biglietteria/eventi (Live Nation): CTA chiaro e ripetuto, percorso d'acquisto corto, fiducia esplicita.

**Applicato**: hero a tutto schermo con slide e titolo lettera per lettera; portfolio editoriale con didascalie sempre visibili e numerazione; reveal allo scroll leggeri (solo `opacity`/`transform`); CTA "Richiedi un preventivo" in nav, hero, ogni skill e contatti; palette chiara con scuro solo in hero e footer; tipografia serif elegante + sans neutro; nessuna libreria.
**Non applicato / da fare con accesso ai siti**: confronto puntuale con palette e font reali dei singoli siti; elenco di *skill* misurabili (mq di ledwall, potenza) da far fornire a Pasquale.

## 3. Scelte del redesign
- Palette: avorio `#f8f4ec`, carta `#fffdf9`, antracite `#1d2127`, oro `#c4a15a` (testi oro scuro `#7a5a1c`), blu notte `#0e1a30`. Contrasti verificati: testo 14,7:1; grigio 6,1:1; oro scuro 5,8:1; avorio su blu notte 15,8:1 (tutti ≥ AA). Quota scura misurata sulla pagina: ~21% desktop, ~23% mobile.
- Tipografia: Playfair Display (titoli) + Inter (testi), file `woff2` locali (nessuna chiamata a Google).
- Intro ridotta, senza canvas né voce sintetica; musica a scelta; `voce.mp3` opzionale.
- Marcatura DEMO: con `APP_MODE=demo` testi/foto generici hanno il bollino "Demo"; in `production` spariscono (e le recensioni vuote nascondono la sezione).
