# Controllo foto (doppioni e qualità)

**Strumento:** `python -m backend.controllo_foto` — cerca foto identiche o quasi identiche, didascalie ripetute, voci mancanti nel
`_manifest.json`, orientamento EXIF sbagliato, foto buie o sfocate. Esce con errore se trova doppioni/incoerenze (usato anche dai test).

## Causa dei doppioni visti online
1. **Avvio simultaneo dei worker** (`gunicorn --workers 2`): ogni worker sincronizzava `foto/organizzate/` nello stesso istante e inseriva
   le stesse foto nuove nel database → ogni foto nuova compariva due volte. Corretto: la sincronizzazione ora è serializzata con un lock
   su file e, a ogni giro, **ripulisce i doppioni già presenti** (resta una riga per foto). Basta `deploy/aggiorna.sh`.
2. **Foto usate sia come immagine di una card «skill» sia in galleria** (es. «Montaggio delle luci sulla struttura» = Allestimenti,
   «Regia audio: mixer digitale» = Audio). Ora le foto già usate nell'hero o nelle card non si ripetono in galleria.

Nei file di `foto/organizzate/` **non c'erano doppioni** (hash dei byte e confronto visivo: 25 foto e 6 video tutti diversi).

## Esito del controllo qualità (25 foto, 6 video)
- **Da scartare:** nessuna. Nessuna foto sfocata (nitidezza minima 318, soglia 60); orientamento corretto in tutte.
- **Scure ma volute** (luci di scena, teatro): `galleria-02`, `galleria-06`, `galleria-10`, `hero-02`, `installazione-08`.
- **Stessa scena, scatti diversi** (tenute, con didascalie diverse): cortile `hero-01` / `hero-03` / `installazione-01` / `installazione-02`; teatro `hero-02` / `galleria-07` / `galleria-08`.
- **Didascalie corrette** perché non descrivevano bene la foto: hero-01/02/03, installazione-01/02, galleria-03/04/13, video-03/04/05 (le vecchie sono in `prima` nel manifest: sul sito già online si aggiornano da sole, senza toccare quelle modificate a mano dall'admin).
- **Locandine video** migliorate (fotogramma più luminoso) per video-03/04/05/06.
