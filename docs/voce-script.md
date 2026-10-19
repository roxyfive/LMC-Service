# Copione per la voce narrante (voce.mp3)

Sono **7 paragrafi, uno per slide dell'intro**: il sito divide la durata del file in 7 parti uguali, quindi tieni i paragrafi
di lunghezza simile (circa 15-25 parole ciascuno, file totale 35-50 secondi). I testi sono **bozze generiche**: fai confermare
a Pasquale quello che dichiara (in particolare la videosorveglianza).

1. Benvenuti in La Music Company Service. Siamo a Napoli e lavoriamo in tutta Italia.
2. Progettiamo e realizziamo la parte tecnica dei vostri eventi, dal palco al meeting.
3. Impianti audio pensati per la sala e per il pubblico, perché ogni parola e ogni nota arrivino chiare.
4. Ledwall e luci trasformano un palco in uno spettacolo.
5. E se serve, installiamo impianti di videosorveglianza per tenere sotto controllo spazi ed eventi.
6. Matrimoni, feste private, concerti e congressi: ovunque ci sia un evento, noi portiamo la tecnica.
7. Raccontateci il vostro evento: prenotate un appuntamento o richiedete un preventivo. Vi aspettiamo.

## Come generare voce.mp3 con ElevenLabs
1. Accedi a elevenlabs.io › **Text to Speech**.
2. Modello: **Eleven Multilingual v2** (o il più recente che supporta l'italiano). Lingua: italiano.
3. Voce: nella *Voice Library* filtra per **Italiano** e scegli una voce calda e professionale (ascolta 2-3 anteprime con la frase 1).
4. Impostazioni indicative: *Stability* 45-55%, *Similarity* 70-80%, *Style* basso (0-15%), *Speaker boost* attivo.
5. Incolla i 7 paragrafi **separati da una riga vuota** e genera. Riascolta tutto: se una parola è pronunciata male, riscrivila foneticamente.
6. Scarica in **MP3** (qualità 128 kbps o più va bene) e rinomina il file **`voce.mp3`**.
7. Mettilo in **`app/static/media/voce.mp3`** (accanto a `music.mp3`), riavvia il sito e apri `/?intro=1`.
   Il pulsante dell'intro diventa "Attiva la musica e la voce": la musica si abbassa mentre la voce parla.
8. Fai commit e push del file se deve andare online. Se un giorno non lo vuoi più, cancellalo: l'intro torna solo musica + didascalie.

Nota: controlla i termini del tuo piano ElevenLabs per l'**uso commerciale** della voce prima di pubblicare.
