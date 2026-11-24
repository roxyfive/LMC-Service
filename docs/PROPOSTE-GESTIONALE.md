# Gestionale LMC — analisi e proposte (FASE 0)

## 1. Cosa mancava rispetto a un gestionale eventi completo
| Area | Prima | Ora (fatto) |
|---|---|---|
| Utenti | un solo login «admin», tutti i poteri | **ruoli** Admin/Collaboratore, utenti creati dal titolare, disattivazione, reset password, **registro attività** |
| Dashboard | elenco appuntamenti | appuntamenti di oggi, richieste nuove, **incassi del mese**, da incassare, scadute, eventi in arrivo, «da fare» |
| Calendario | solo elenco + disponibilità settimanale | **agenda mensile a colori** (libero / impegnato / da confermare / bloccato), dettaglio giorno, conferma/annulla, blocco giorno, note |
| Fatture | PDF semplice, numero a contatore | **bozza → emessa → pagata/scaduta**, numerazione progressiva configurabile, IVA, dati fiscali, **PDF elegante**, stato SDI |
| Acconti | assenti | pagamenti parziali su preventivo/fattura/evento, saldato/parziale, riepilogo |
| Recensioni | inserimento a mano | **richiesta post-evento via email**, pagina pubblica con stelle, **approvazione** prima della pubblicazione |
| Galleria | caricamento libero | **didascalia obbligatoria**, tipo/data evento, collegata a evento/fattura, **parte nascosta**, «Pubblica» |
| Tariffe | assenti | listino base, usato in preventivi/fatture e nella **stima del configuratore** (facoltativa) |
| Statistiche | visite al sito | incassi per mese/anno, eventi per tipo, servizi richiesti, **conversione** richieste→confermate |
| WhatsApp | solo impostazioni | pagina stato + **«Riepilogo» manuale** su ogni richiesta/appuntamento |
| Materiale | elenco magazzino | (invariato: vedi proposta 1) |

## 2. Funzioni UNICHE per un service audio/luci — **in attesa del tuo OK**
Sono le proposte «grandi»: non le ho implementate senza conferma. Stima di sforzo: **S** = mezza giornata · **M** = 1–2 giorni · **L** = 3+ giorni.

1. **Check-list attrezzatura per evento + prenotazione per data** — *M/L (il più utile)*
   Sull'evento scegli attrezzatura e quantità; il sistema controlla il **magazzino per data** («servono 12 teste mobili, ne hai 12 ma 8 sono già prenotate il 14/11 per un altro evento») e segnala i conflitti. La check-list si spunta dal telefono in 3 momenti: *caricato sul furgone → montato → rientrato in magazzino*, con note su guasti (l'attrezzo passa «in riparazione»).
2. **Foglio tecnico (rider) PDF scaricabile** — *M*
   Un PDF per evento con: elenco attrezzatura e quantità, potenze/consumi, orari, referenti, indirizzo con mappa, note sala. Si manda al cliente/location in un clic (email o WhatsApp). Si genera dalla check-list.
3. **Timeline montaggio/smontaggio** — *M*
   Per ogni evento: carico, partenza, arrivo, montaggio, soundcheck, show, smontaggio, rientro, con orari e persona assegnata. Vista del giorno per il collaboratore e **promemoria WhatsApp** all'orario di carico.
4. **Calcolo potenza e prese** — *S*
   Somma dei watt dell'attrezzatura dell'evento e avviso se supera la potenza disponibile in sala (es. 3 kW): evita i blackout a metà serata. Si appoggia ai campi «potenza» aggiunti al magazzino.
5. **Preventivo a pacchetti con accettazione online** — *M*
   Dal configuratore o dalla richiesta nasce un preventivo con pacchetti (Base/Plus/Show) dal listino tariffe; il cliente lo apre da un link, **accetta** e versa l'acconto; lo stato passa da solo a «accettato» e compare in agenda come «da confermare».

Consiglio d'ordine: 1 → 2 → 3 (sono collegate e risolvono i problemi di tutti i giorni), poi 4 e 5.

## 3. Cosa fare adesso (tu)
* Compilare **Fatture › Dati fiscali** (P.IVA, sede, IBAN, numerazione) e **Tariffe** (prezzi veri: ora sono a 0 e disattivate).
* Creare l'utente del collaboratore da **Utenti e permessi** e farlo accedere (cambia da solo la password).
* Scrivermi «ok» sulle proposte da 1 a 5 che vuoi.
