# Fatturazione elettronica (SDI): cosa fa il gestionale e cosa serve

## Cosa fa oggi il gestionale
* Crea la fattura (bozza), assegna **numero progressivo** all'emissione, calcola imponibile/IVA/totale, tiene **scadenza, acconti e incassi**.
* Produce il **PDF «copia di cortesia»** con i tuoi dati (ragione sociale, P.IVA, sede, IBAN) e quelli del cliente (P.IVA/C.F., codice destinatario, PEC).
* Per ogni fattura puoi segnare lo **stato SDI**: *non inviata · inviata · consegnata · scartata · mancata consegna* (+ nota con l'identificativo o il motivo dello scarto).

## Cosa NON fa (ancora)
La **fattura elettronica valida** è il file **XML FatturaPA** trasmesso al **Sistema di Interscambio (SDI)**: il PDF non ha valore fiscale. L'app non genera né trasmette l'XML.

## Cosa serve per trasmettere (scegli UNA strada)
1. **Portale gratuito «Fatture e Corrispettivi»** dell'Agenzia delle Entrate (accesso con SPID/CIE/CNS): ricopi i dati della fattura emessa dal gestionale e il portale crea e invia l'XML.
2. **Intermediario / software di fatturazione** (es. Aruba, Fatture in Cloud, Danea…) o il **commercialista**: gli passi i dati; l'XML lo creano loro.
3. *(Sviluppo futuro, da concordare)* **esportazione XML FatturaPA** dal gestionale + invio tramite intermediario con API: serve un accordo con il fornitore scelto e i dati sotto.

## Dati indispensabili (da inserire in Fatture › Dati fiscali e in Clienti)
| Chi | Cosa |
|---|---|
| Tu (cedente) | ragione sociale, **Partita IVA**, codice fiscale, sede legale, **regime fiscale** (ordinario / forfettario…), PEC, IBAN |
| Cliente azienda | ragione sociale, **P.IVA**, sede, **codice destinatario (7 caratteri)** o **PEC** |
| Cliente privato | **codice fiscale**, indirizzo (codice destinatario `0000000`) |
| Fattura | numero progressivo, data, imponibile, **aliquota IVA o natura** (es. N2.2 per il forfettario), totale, scadenza |

## Regime forfettario o IVA esente
Imposta «IVA predefinita» a **0** e scrivi la dicitura (es. *«Operazione effettuata ai sensi dell'art. 1, commi 54-89, L. 190/2014. Non soggetta a IVA»*) in «Dicitura di regime»: compare sul PDF. La *natura* dell'operazione per l'XML la gestisce il portale/intermediario.

## Tempi e regole utili
* La fattura va trasmessa **entro 12 giorni** dall'operazione (salvo casi particolari).
* Una fattura **scartata** dall'SDI si corregge e si reinvia con lo stesso numero: segna «scartata» nella nota il motivo e crea la correzione col tuo intermediario.
* Conserva i file XML (obbligo di conservazione 10 anni: il portale AdE offre la conservazione gratuita se aderisci).
* Questo documento è informativo: per regime, aliquote e natura dell'IVA chiedi al tuo commercialista.
