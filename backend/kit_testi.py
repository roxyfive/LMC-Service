"""Contenuti delle due guide PDF del kit (testo in italiano semplice, pensato per chi non è tecnico).

Struttura di ogni sezione:  dict(id, titolo, intro, passi=[...], nota=str, schema=str (ASCII), img=nome screenshot, tecnica=[...])
"""

VERSIONE = "1.0"

FLUSSO_PRATICA = """\
 +-----------+   +-------------+   +------------+   +-----------+   +----------+   +---------+
 | RICHIESTA |-->| PREVENTIVO  |-->| CONFERMATO |-->|  FATTURA  |-->| ACCONTI  |-->| SALDATO |
 | dal sito  |   | prezzi da   |   | entra in   |   | numero    |   | anche a  |   | pratica |
 | o telefono|   | Tariffe     |   | Agenda     |   | progress. |   | rate     |   | chiusa  |
 +-----------+   +-------------+   +------------+   +-----------+   +----------+   +---------+

 Stato della fattura:   BOZZA --> EMESSA --> PARZIALE --> PAGATA
                        (se passa la scadenza senza saldo: SCADUTA, in rosso)

 Dopo la conferma di un appuntamento il gestionale ti propone da solo
 di creare la fattura e di registrare l'acconto.
"""

FLUSSO_RUOLI = """\
                      +-------------------------------+
                      |            ADMIN              |
                      |  (titolare: vede e fa tutto)  |
                      +---------------+---------------+
                                      |
        +-----------------------------+-----------------------------+
        |                             |                             |
  SOLO ADMIN                    ADMIN + COLLABORATORE         SEMPRE REGISTRATO
  - Fatture                     - Agenda / Calendario         - chi ha fatto cosa,
  - Acconti e incassi           - Richieste                     quando (Registro attività,
  - Statistiche incassi         - Galleria (carica foto)        visibile solo all'admin)
  - Tariffe                     - Materiale e check-list
  - Impostazioni                - Assistente
  - Utenti e permessi
"""

FLUSSO_RECENSIONE = """\
  evento finito --> il giorno dopo parte l'email --> il cliente apre il link --> sceglie le stelle
   (appuntamento       "com'è andata?" (SMTP)          /recensione/<codice>        e scrive due righe
    confermato)                                                                          |
                                                                                         v
   sul sito compare  <-- tu APPROVI in  <-- la recensione arriva "in attesa" <-----------+
   (stelle + nome +      Admin > Recensioni   (non è mai pubblica da sola)
    evento)
"""

FLUSSO_GALLERIA = """\
  carichi la foto --> didascalia obbligatoria --> parte NASCOSTA --> controlli --> PUBBLICA
  (admin o            (cosa è, che evento,          (bozza: nessuno    l'anteprima   (solo l'admin
   collaboratore)      che data)                     la vede)                         può pubblicarla)
"""

SPEC_TECNICHE = [
    ("Applicazione", "Flask (Python 3) + SQLite in modalità WAL; pagine HTML (Jinja) con JavaScript e CSS semplici, installabile come app (PWA)."),
    ("Server", "VPS IONOS, gunicorn dietro nginx con HTTPS; indirizzo https://lmcservice.duckdns.org"),
    ("Database", "Un solo file SQLite nella cartella dati; backup automatico alle 03:20 (copia locale + Google Drive «lmc»)."),
    ("Accessi", "Login con password; ruoli ADMIN e COLLABORATORE; ogni pagina controllata lato server (deny-by-default)."),
    ("Sicurezza", "Protezione CSRF su tutte le azioni, cookie HttpOnly, limite tentativi di accesso, password mai salvate in chiaro."),
    ("Registro attività", "Ogni azione sensibile (fatture, incassi, utenti, impostazioni, galleria) salva chi, cosa e quando."),
    ("Email", "Server SMTP configurato nel file .env (promemoria appuntamenti, richiesta recensione)."),
    ("WhatsApp", "Twilio (se configurato): report automatici; riepilogo manuale con un clic su ogni richiesta o appuntamento."),
    ("Aggiornamento", "Dopo ogni modifica: sudo bash /srv/lmc/deploy/aggiorna.sh (guarda il backup, scarica il codice, riavvia)."),
    ("PDF", "Fatture e preventivi generati dal server con ReportLab: intestazione con i dati dell'azienda, IVA e totale."),
]

# ------------------------------------------------------------------ GUIDA ADMIN
ADMIN = [
    dict(id="inizio", titolo="1. Iniziare: accesso e menu", img="admin-dashboard-desktop",
         intro="Il gestionale è un sito riservato: lo apri da telefono o computer, come un'app. Dopo l'accesso vedi un menu a sinistra (su telefono: il pulsante in alto) con solo le voci che il tuo ruolo può usare.",
         passi=["Scansiona il QR «Accesso Admin» (o scrivi l'indirizzo /admin dopo quello del sito).",
                "Inserisci utente e password. La prima volta ti viene chiesto di cambiare la password: scegline una lunga che non usi altrove.",
                "Sei nella Dashboard. Dal menu raggiungi tutte le altre sezioni.",
                "Per installarlo come app: dal menu del browser scegli «Aggiungi a schermata Home».",
                "Per uscire usa sempre «Esci» in fondo al menu, soprattutto su telefoni condivisi."],
         nota="Se dimentichi la password: un altro ADMIN la reimposta da Utenti (vedi sezione Team e permessi)."),
    dict(id="dashboard", titolo="2. Dashboard", img="admin-dashboard-desktop",
         intro="La pagina da aprire ogni mattina: in un colpo d'occhio cosa succede oggi e cosa richiede una risposta.",
         passi=["Appuntamenti di oggi: orario, cliente e stato; tocca per aprire il giorno nell'Agenda.",
                "Nuove richieste: i contatti arrivati dal sito che non hai ancora gestito.",
                "Incassi del mese: somma dei pagamenti registrati (vedi solo se sei ADMIN).",
                "Prossimi eventi: i lavori confermati dei giorni successivi.",
                "Suggerimenti: dopo aver confermato un appuntamento compare l'invito a creare fattura o acconto."]),
    dict(id="agenda", titolo="3. Agenda e calendario", img="admin-agenda-desktop",
         intro="Il calendario mensile con i giorni colorati. È collegato alla disponibilità mostrata sul sito: se blocchi un giorno qui, i clienti non lo possono prenotare.",
         passi=["Apri Agenda: ogni giorno ha un colore (libero, con richieste, confermato, bloccato).",
                "Tocca un giorno: vedi gli appuntamenti con orario, nome e telefono.",
                "Azioni rapide su ogni appuntamento: Conferma, Rifiuta, Cambia stato.",
                "«Blocca giorno» chiude la data ai clienti (ferie, evento già pieno). «Sblocca» la riapre.",
                "Il campo Note del giorno serve per appunti interni (non li vede nessun cliente)."],
         nota="Il cliente riceve un promemoria email il giorno prima di ogni appuntamento confermato."),
    dict(id="richieste", titolo="4. Richieste e preventivi", img="admin-richieste-desktop",
         intro="Qui arrivano i moduli compilati sul sito (preventivi e prenotazioni). Da qui parte tutto il flusso della pratica.",
         passi=["Apri Richieste: le nuove sono in evidenza.",
                "Tocca una richiesta per vedere tutti i dettagli: evento, data, luogo, servizi, note.",
                "«Invia riepilogo WhatsApp» apre WhatsApp con il messaggio già scritto (lo mandi tu con un tocco).",
                "Cambia lo stato (in attesa, confermato, annullato). Confermando, la data entra in Agenda.",
                "In Preventivi crei un documento con le voci di prezzo (prese da Tariffe) e lo scarichi in PDF.",
                "Un preventivo accettato si trasforma in fattura con un clic."],
         schema=FLUSSO_PRATICA),
    dict(id="fatture", titolo="5. Fatture", img="admin-fattura-desktop",
         intro="Fatture di cortesia in PDF con i tuoi dati aziendali. Il numero progressivo si assegna solo quando EMETTI la fattura, così non restano buchi nella numerazione.",
         passi=["Prima volta: Fatture > Dati fiscali. Compila ragione sociale, P.IVA, codice fiscale, sede, IBAN, IVA predefinita e numerazione (prefisso, cifre, numero di partenza).",
                "«Nuova fattura» (vuota) oppure «Da richiesta/preventivo» per precompilare cliente e importi.",
                "Controlla le voci, l'imponibile e l'IVA. Salva: resta in BOZZA, senza numero.",
                "«Emetti»: viene assegnato il numero (es. F2026-001) e la data. Non si cambia più.",
                "«PDF» scarica la fattura elegante da inviare al cliente.",
                "Stati: bozza, emessa, parziale, pagata, scaduta. «Annulla» tiene il numero tracciato e non lo riusa.",
                "SDI: segni a mano se la fattura elettronica è stata inviata/accettata (il PDF non sostituisce l'XML, vedi sotto)."],
         nota="Fattura elettronica: questo PDF è una copia di cortesia. L'invio allo SDI si fa col tuo commercialista o un software di fatturazione elettronica; trovi i dettagli in docs/FATTURAZIONE-SDI.md.",
         tecnica=["Numero: prefisso + anno + progressivo (configurabile); azzeramento annuale opzionale.",
                  "Calcolo: imponibile + IVA % = totale, con arrotondamento a 2 decimali.",
                  "Numero assegnato dentro una transazione protetta: impossibile avere due fatture con lo stesso numero."]),
    dict(id="acconti", titolo="6. Acconti e incassi", img="admin-acconti-desktop",
         intro="Registri ogni pagamento ricevuto, anche a rate. Il sistema calcola da solo cosa resta da incassare e aggiorna lo stato della fattura.",
         passi=["Apri Acconti: elenco delle pratiche con importo, versato e residuo.",
                "Su una fattura o pratica premi «Registra pagamento»: data, importo, metodo (bonifico, contanti, carta, altro), nota.",
                "Se il versato è minore del totale lo stato diventa PARZIALE; quando arriva al totale, PAGATA.",
                "«Segna come pagata» registra in automatico il residuo in un solo passaggio.",
                "In alto vedi i totali: incassato, da incassare, scaduto.",
                "Un pagamento sbagliato si elimina dalla riga (resta nel Registro attività)."],
         nota="Gli incassi del mese in Dashboard e in Statistiche sono la somma di questi pagamenti: registrarli è l'unico modo per avere numeri esatti."),
    dict(id="recensioni", titolo="7. Recensioni", img="admin-recensioni-desktop",
         intro="Chiedi al cliente un parere dopo l'evento e scegli tu cosa pubblicare. Una recensione non appare mai sul sito senza la tua approvazione.",
         passi=["Dopo un evento concluso parte da sola un'email con un link personale (se SMTP e indirizzo del sito sono configurati).",
                "Oppure da Recensioni premi «Richiedi» su un cliente per inviarla subito.",
                "Il cliente sceglie le stelle e scrive due righe.",
                "Tu apri Recensioni: leggi, poi «Approva» (compare sul sito con stelle, nome ed evento) oppure «Rifiuta».",
                "Puoi anche inserire a mano una recensione ricevuta su WhatsApp."],
         schema=FLUSSO_RECENSIONE),
    dict(id="galleria", titolo="8. Galleria eventi", img="admin-galleria-desktop",
         intro="Le foto dei lavori. Ogni foto ha una didascalia obbligatoria e parte nascosta: la pubblichi solo quando sei sicuro.",
         passi=["Galleria > «Carica foto»: scegli i file dal telefono o dal computer.",
                "Scrivi la didascalia (obbligatoria), scegli il tipo di evento e la data.",
                "Facoltativo: collega la foto a un evento o a una fattura.",
                "Le foto nuove sono in «Bozze». Con «Pubblica» compaiono sul sito; «Nascondi» le toglie.",
                "Trascina per cambiare l'ordine. «Elimina» rimuove definitivamente (solo ADMIN)."],
         nota="Il COLLABORATORE può caricare foto ma restano sempre nascoste: la pubblicazione è decisione dell'ADMIN.",
         schema=FLUSSO_GALLERIA),
    dict(id="tariffe", titolo="9. Tariffe (listino)", img="admin-tariffe-desktop",
         intro="Il listino base dei prezzi: serve a compilare i preventivi più in fretta e, se vuoi, a mostrare una stima nel configuratore del sito.",
         passi=["Apri Tariffe: trovi le voci già pronte (impianto audio, luci, DJ, ecc.) con prezzo 0 e disattivate.",
                "Scrivi il prezzo di ogni voce e l'unità («a evento», «a ora», «a giorno»).",
                "Attiva le voci che vuoi usare. Quelle disattive restano nascoste.",
                "Per mostrare la stima ai clienti sul configuratore attiva «Tariffe pubbliche».",
                "Cambiare un prezzo non modifica i preventivi e le fatture già fatti."],
         nota="Compila le tariffe prima di consegnare il gestionale ai collaboratori: i preventivi partono da qui."),
    dict(id="statistiche", titolo="10. Statistiche", img="admin-statistiche-desktop",
         intro="Numeri chiari per capire come va il lavoro. Solo per ADMIN.",
         passi=["Incassi per mese e per anno (dai pagamenti registrati).",
                "Eventi per tipo: quanti matrimoni, compleanni, eventi aziendali.",
                "Servizi più richiesti dal configuratore.",
                "Conversione: quante richieste diventano eventi confermati.",
                "Cambia l'anno dal selettore in alto."]),
    dict(id="team", titolo="11. Team, utenti e permessi", img="admin-utenti-desktop",
         intro="Qui decidi chi può entrare e cosa può fare. Esistono due ruoli: ADMIN (tutto) e COLLABORATORE (solo il lavoro operativo).",
         passi=["Apri Utenti > «Nuovo utente»: nome, utente, email, ruolo e una password iniziale.",
                "Al primo accesso la persona deve cambiare la password.",
                "Per sospendere qualcuno senza cancellarlo premi «Disattiva» (non potrà più entrare, la sua storia resta).",
                "«Reimposta password» genera una nuova password temporanea.",
                "Non puoi disattivare o declassare l'ultimo ADMIN: così non rimani mai fuori.",
                "Il Registro attività elenca chi ha fatto cosa e quando."],
         nota="Un COLLABORATORE che prova ad aprire Fatture, Acconti, Statistiche, Tariffe, Impostazioni o Utenti vede la pagina «Accesso non consentito» e il tentativo non apre nulla."),
    dict(id="whatsapp", titolo="12. WhatsApp", img="admin-whatsapp-desktop",
         intro="Due strumenti: la pagina di stato di Twilio (report automatici) e il riepilogo manuale.",
         passi=["Pagina WhatsApp: vedi se Twilio è attivo, i destinatari dei report e gli ultimi invii.",
                "Su ogni richiesta o appuntamento «Invia riepilogo» prepara il messaggio con data, cliente e servizi.",
                "Tocca il pulsante: si apre WhatsApp con il testo pronto, lo invii tu.",
                "Se Twilio non è configurato la pagina lo dice chiaramente: nulla si rompe."]),
    dict(id="backup", titolo="13. Backup e sicurezza dei dati", img="admin-backup-desktop",
         intro="Il database viene copiato ogni notte alle 03:20 in locale e su Google Drive. Qui controlli che sia andato tutto bene.",
         passi=["Apri Backup: data e ora dell'ultima copia e dove è finita.",
                "Se la data è vecchia di più di un giorno, avvisa chi gestisce il server.",
                "Prima di ogni aggiornamento (aggiorna.sh) il server controlla anche il backup e si ferma se è mancante.",
                "Per recuperare un dato cancellato serve l'aiuto di chi gestisce il server: non è un'operazione da fare dal gestionale."]),
    dict(id="impostazioni", titolo="14. Impostazioni e cosa compilare", img="admin-dashboard-desktop",
         intro="Prima di usare il gestionale davvero, compila queste cose una sola volta.",
         passi=["Fatture > Dati fiscali: ragione sociale, P.IVA, codice fiscale, sede, IBAN, IVA, numerazione.",
                "Tariffe: i prezzi di ogni voce del listino.",
                "Impostazioni > Testi: «Sito ufficiale» (URL del sito), telefono, email di contatto.",
                "File .env sul server: PUBLIC_URL (link nelle email di recensione) e i dati SMTP.",
                "Utenti: crea un account COLLABORATORE per ogni persona del team (mai condividere la tua password)."]),
]

# ------------------------------------------------------------------ GUIDA CLIENTE (sito / app, per Pasquale e collaboratori)
CLIENTE = [
    dict(id="sito", titolo="1. Il sito in breve", img="sito-home-desktop",
         intro="Il sito di La Music Company Service è la vetrina e il banco di prenotazione: i clienti ci arrivano da Google, Instagram o dal QR sui materiali stampati.",
         passi=["Home: chi siamo, servizi principali, numero di telefono sempre a portata di tocco.",
                "Pulsante «Richiedi preventivo»: apre il modulo.",
                "Menu in alto: Skill, Galleria, Show demo, Configuratore, Contatti.",
                "Funziona benissimo da telefono e si può installare come app."]),
    dict(id="app", titolo="2. Installare l'app sul telefono", img="sito-home-mobile",
         intro="Il sito si installa come un'app: icona sulla schermata Home, apertura a tutto schermo, nessun download da store.",
         passi=["Scansiona il QR «App clienti» con la fotocamera.",
                "iPhone (Safari): tocca Condividi, poi «Aggiungi a Home».",
                "Android (Chrome): menu a tre puntini, poi «Installa app» o «Aggiungi a schermata Home».",
                "L'icona LMC compare tra le app. Toccala per aprire il sito."]),
    dict(id="skill", titolo="3. Servizi e competenze", img="sito-skill-desktop",
         intro="La sezione dove spieghiamo cosa sappiamo fare: audio, luci, palchi, video.",
         passi=["Scorri le schede dei servizi: ognuna spiega in poche righe cosa include.",
                "Tocca una scheda per avere più dettagli.",
                "In fondo trovi sempre il pulsante per chiedere un preventivo."]),
    dict(id="galleria", titolo="4. Galleria e Show demo", img="sito-galleria-desktop",
         intro="Le foto vere dei nostri lavori e i video degli allestimenti.",
         passi=["Galleria: foto con didascalia (che evento, che data). Tocca per ingrandire.",
                "Show demo: video degli allestimenti, a partire dal reel dell'America's Cup.",
                "Le foto nuove compaiono solo dopo che l'ADMIN le ha pubblicate."]),
    dict(id="conf", titolo="5. Configuratore e preventivo", img="sito-configuratore-desktop",
         intro="Il cliente sceglie evento, ospiti e servizi e ottiene una prima idea (e, se attivata, una stima di prezzo).",
         passi=["Scegli il tipo di evento e la data.",
                "Seleziona i servizi: audio, luci, DJ, palco, video.",
                "Se le tariffe pubbliche sono attive vedi una stima indicativa.",
                "Compila nome, telefono ed email e invia: la richiesta arriva nel gestionale e a WhatsApp."],
         nota="La stima è sempre indicativa: il prezzo definitivo è quello del preventivo ricevuto."),
    dict(id="prenota", titolo="6. Prenotare un appuntamento", img="sito-form-desktop",
         intro="Il cliente sceglie un giorno libero e un orario per parlare con noi.",
         passi=["Apri il modulo di prenotazione.",
                "Scegli una data: i giorni bloccati o già pieni non si possono selezionare.",
                "Indica nome, telefono, tipo di evento e note.",
                "Riceve una conferma e, il giorno prima, un promemoria via email."]),
    dict(id="contatti", titolo="7. Contatti e recensioni", img="sito-contatti-desktop",
         intro="Telefono, WhatsApp, email, mappa e social in un unico posto. Sul sito compaiono anche le recensioni approvate.",
         passi=["Tocca il telefono o WhatsApp per chiamare o scrivere subito.",
                "Dopo un evento il cliente riceve un link per lasciare le stelle e un commento.",
                "Solo le recensioni approvate dall'ADMIN compaiono sul sito."]),
    dict(id="collab", titolo="8. Per i collaboratori: cosa puoi fare", img="admin-collab-dashboard-desktop",
         intro="Se ti hanno dato un account COLLABORATORE vedi solo gli strumenti per il lavoro quotidiano.",
         passi=["Agenda: vedi gli appuntamenti, confermi, blocchi giorni e scrivi note.",
                "Richieste: leggi le richieste e mandi il riepilogo su WhatsApp.",
                "Galleria: carichi le foto dell'evento con la didascalia (le pubblica l'ADMIN).",
                "Materiale e check-list: controlli l'attrezzatura da portare.",
                "Fatture, incassi, statistiche, tariffe e impostazioni non sono visibili: è normale.",
                "Ogni tua azione è registrata: serve a tutelare tutti."],
         schema=FLUSSO_RUOLI),
]
