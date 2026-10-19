# Proposte di miglioria (frutto dell'audit tecnico e della ricerca web)

Fonti: revisione del codice fatta da un agente di sola lettura e ricerca web (WebSearch; i siti dei concorrenti sono bloccati dall'ambiente,
quindi le idee sul "mercato" sono best practice generali, non analisi dei singoli siti). Priorità: **A** subito · **B** presto · **C** quando serve.

## Già implementate in questa versione
| # | Miglioria | Perché |
|---|---|---|
| 1 | **Come lavoriamo** a 4 step | Riduce l'attrito di chi non sa cosa chiedere. Testi indicativi (marcati DEMO) da confermare. |
| 2 | **Configuratore "Costruisci il tuo evento"** (senza prezzi) | Guida il cliente e precompila il preventivo; nessun prezzo inventato. |
| 3 | **FAQ** con risposte basate solo su dati reali | Meno domande ripetitive. Non usa lo schema FAQ (Google dal 2023 non mostra più il rich result ai siti non istituzionali). |
| 4 | **Scorciatoie dell'app installata** (Preventivo, Emergenza, Prenota) + cache senza dati personali | PWA più utile; le pagine con token (`/appuntamento/…`) non finiscono più nella cache del telefono. |
| 5 | Sicurezza: segreti in tabella separata, rate limit, SECRET_KEY stabile, `/media` nascosti, indice anti doppia prenotazione, WAL | Dall'audit tecnico. |

## Da fare
| Pri. | Proposta | Note / rischi | Difficoltà |
|---|---|---|---|
| A | **Foto reali di Pasquale** al posto delle demo (hero, galleria, skill) | È ciò che più alza la qualità percepita. Lo script `importa_social.py` è pronto. | S |
| A | **Google Business Profile** curato (categorie, area servita, orari 24h, foto, link al sito) | Nessuna recensione inventata; dati coerenti con il sito (NAP). | S |
| A | **Informativa privacy completa** (Twilio, Vapi, AI, tempi) + parere di un consulente | Obbligatorio prima di usare chat/voce/WhatsApp con clienti veri. | S |
| A | **Template WhatsApp approvati** e prova in produzione | Senza, i report fuori dalle 24 ore non arrivano. | S |
| B | **Portfolio per tipologia** (matrimoni, live, congressi) con pagina per evento | Solo lavori veri e con permesso; niente "prima/dopo" costruiti. | M |
| B | **Prima/dopo** per allestimenti | Solo con coppie di foto reali (cartella dedicata). | M |
| B | **Testimonianze** con foto/video dalla storia "Dicono di noi" | Con consenso scritto; mai inventate. | S |
| B | **Aggiungi al calendario (.ics)** per gli appuntamenti + promemoria WhatsApp al cliente | Con opt-in esplicito e template approvato. | M |
| B | **Multilingua** (inglese) per matrimoni di stranieri e aziende | Traduzioni da far rivedere; hreflang. | M |
| B | **Numerazione fatture** a prova di cancellazione e login admin con cambio password | Debiti tecnici trovati dall'audit (`COUNT(*)+1`, account unico). | M |
| C | **Area clienti** (stato del preventivo, documenti) | Ha senso solo con molti clienti ricorrenti. | L |
| C | **Notifiche push** della PWA | Su iOS ci sono limiti; servono consenso e un uso sobrio. | L |
| C | **Analisi eventi di click** (tel, WhatsApp, richiamami) nei report | Conteggi anonimi come le visite. | S |
| C | Test automatici su più worker/concorrenza e CSP (Content-Security-Policy) con Vapi | L'audit consiglia di scrivere la CSP prima di andare in produzione. | M |

## Da NON fare
1. Inventare prezzi, clienti, premi, recensioni, certificazioni o foto "prima/dopo".
2. Mandare WhatsApp fuori finestra 24 ore senza template approvato e senza opt-in, o pre-spuntare i consensi.
3. Far partire l'assistente AI/voce prima dell'informativa privacy, o dichiarare "24 ore" e tempi di intervento che non si garantiscono davvero.

## Debiti tecnici trovati dall'audit e non toccati
`manage()` consente di "modificare" appuntamenti annullati; `int(request.form[...])` senza validazione in alcune pagine admin;
sessione admin non "permanente"; test come script (non pytest) e dipendenze non bloccate; backup in chiaro che ora contiene anche le chiavi API.
