# Foto e video reali del sito

Il sito legge **queste cartelle** all'avvio (e dal pulsante *Sincronizza cartella* in Admin › Foto).
Ogni file nuovo viene ottimizzato (webp 480/960/1600) e pubblicato automaticamente.

| Cartella          | Cosa contiene                         | Dove appare nel sito                          |
|-------------------|---------------------------------------|-----------------------------------------------|
| `hero/`           | 1-3 foto orizzontali di grande impatto | sfondo in cima alla home (la prima in ordine alfabetico) e intro |
| `galleria/`       | foto degli eventi                     | sezione *Eventi realizzati* (categoria Eventi) |
| `installazioni/`  | foto di allestimenti e impianti       | sezione *Eventi realizzati* (filtro Installazioni) |
| `video/`          | video mp4 (max 60 MB ciascuno)        | sezione *Show demo*                           |

- Formati: jpg, png, webp (foto) · mp4, mov (video).
- Nomi consigliati: `hero-01.jpg`, `galleria-01.jpg`, `installazione-01.jpg`, `video-01.mp4`.
  Li crea da solo `python importa_social.py <export.zip>`.
- Finché una cartella è vuota il sito mostra i segnaposto (marcati "FOTO IN ARRIVO");
  appena arrivano foto vere i segnaposto vengono nascosti.
- Per **togliere** una foto dal sito eliminala anche da qui, altrimenti alla prossima sincronizzazione ritorna.
- `_manifest.json` (creato dall'importatore) conserva data e didascalia originali: il sito li usa come titolo.
