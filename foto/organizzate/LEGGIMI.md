# Foto e video reali del sito

Queste cartelle contengono le **foto e i video reali di LMC Service** (crediti in `CREDITI.md`):
`hero/` (le 3 panoramiche della slideshow in cima), `installazioni/` (palchi, impianti, luci, attrezzature), `galleria/` (il lavoro sul campo) e
`video/` (il primo video, `video-01.mp4`, è quello **in evidenza** nella sezione «Show demo»).

## Come aggiungere o sostituire foto
1. **Dal pannello admin** (Foto e video › Carica) per una o poche foto.
2. **Da cartella**: copia le foto nella sottocartella giusta, poi:
   `python -m backend.enhance_foto` (migliora esposizione/colore/rumore/nitidezza; sovrascrive e salva gli originali in `foto/_originali/`),
   poi riavvia il sito o premi *Sincronizza cartella* in Admin › Foto.
3. Le didascalie si scrivono in `_manifest.json` (campo `caption`).

## Regole di sincronizzazione
- Una foto con lo **stesso nome ma contenuto diverso** sostituisce la vecchia.
- Una foto **cancellata o spostata** dalle cartelle sparisce anche dal sito alla sincronizzazione (non restano «foto fantasma»).
- I video si caricano fino a **60 MB** (ricomprimi con ffmpeg se più grandi: `ffmpeg -i in.mp4 -c:v libx264 -crf 22 -c:a aac -movflags +faststart out.mp4`).
  Accanto a ogni video può stare la sua locandina `nome.poster.jpg`.
- Le cartelle non vuote non vengono mai svuotate per errore: la pulizia agisce solo se nelle cartelle c'è almeno un file.
