# Foto e video reali del sito

> ⚠️ **ATTENZIONE: le foto che trovi ora in queste cartelle sono DEMO temporanee** (1 hero, 1 galleria,
> 3 installazioni), non sono lavori di LMC Service. Vedi `CREDITI.md`. Vanno sostituite con le foto reali.

## Come sostituire le foto demo (3 modi, dal più semplice)

1. **Stesso nome, nuovo file.** Copia la foto vera dentro la cartella giusta con **lo stesso nome** di quella demo
   (es. `hero/hero-01.jpg`) e conferma la sostituzione. Riavvia il sito (o Admin › Foto › Sincronizza):
   la nuova foto viene pubblicata e quella vecchia resta nascosta nell'archivio del sito.
2. **Rilancia l'importatore.** Metti tutte le foto/video del cliente (anche in sottocartelle o ZIP, da WhatsApp o Drive)
   in `foto/da_social/` e lancia `python importa_social.py foto/da_social`. Le smista da solo in
   hero / galleria / installazioni / video con nomi in ordine.
3. **Dal pannello admin.** Admin › Foto › carica le foto, poi nascondi o elimina quelle demo.

Per **eliminare** le demo basta cancellare i file `*-01.jpg` demo dalle cartelle (e poi anche dall'Admin › Foto,
con *Elimina*, se il sito è già stato avviato) e cancellare `CREDITI.md`.
Finché una cartella è vuota il sito usa i segnaposto "FOTO IN ARRIVO".

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

## Come il sito usa le foto (home animata)
- **Hero e intro:** le foto in `hero/` e `galleria/` fanno le slide in cima alla home; l'intro cinematografica usa le foto delle skill e la hero.
- **Sezione "Le nostre skill"** (Videosorveglianza, Ledwall, Audio, Allestimenti, Eventi): per ogni skill il sito sceglie da solo
  la foto che nel **nome file o nella didascalia** contiene una parola chiave: *telecamera/sorveglianza*, *ledwall*, *audio/casse/mixer*,
  *allestimento/palco/truss*, *concerto/evento/matrimonio*. Esempio: `ledwall-matrimonio.jpg`. Senza parole chiave usa le altre foto a rotazione.
  Con `importa_social.py` il nome originale resta in `_manifest.json` e viene usato allo stesso modo.
- **Voce narrante dell'intro:** di default usa la voce del browser (Web Speech API, italiano). Per una voce registrata metti il file
  `app/static/media/voce.mp3` (circa 40-60 secondi): se esiste viene usato al posto della voce di sistema. I testi della narrazione
  sono in `backend/vetrina.py` (`INTRO_STEPS`).
