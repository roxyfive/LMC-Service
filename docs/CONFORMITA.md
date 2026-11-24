# Conformità del sito LMC (checklist TikTok «sito a norma») — verificata il 2 novembre 2026

Esclusi, come richiesto, i **dati professionali** (P.IVA, sede, ecc.): li inserisce il titolare da Admin.
Controllo automatico: `python -m tests.test_conformita` (45 verifiche, incluse axe WCAG 2.2 AA su home, privacy e accessibilità).

| # | Voce | Esito | Cosa c'è |
|---|---|---|---|
| 1 | Privacy policy | ✅ | `/privacy`: titolare, tabella dati/finalità/base giuridica/conservazione, fornitori ed extra-UE, diritti, Garante |
| 2 | Banner cookie chiari | ✅ non necessario | Solo il cookie tecnico `session` (HttpOnly, Secure, Lax) e `introSeen` in sessionStorage: niente analytics, niente pixel, niente embed. Spiegato nell'informativa (§3). **Se aggiungi Google Analytics, Meta Pixel, mappe o video YouTube serve un banner con consenso PRIMA di caricarli.** Il test fallisce se compare una risorsa esterna. |
| 3 | Informativa moduli | ✅ | Su prenotazione e preventivo: riga di informativa breve (finalità, conservazione, titolare) + presa visione col link; recensione con consenso alla pubblicazione; email ai clienti con nota privacy e come non riceverne altre |
| 4 | Solo dati necessari | ✅ | Campi minimi (data evento e note facoltativi), chat scritta non archiviata, email della recensione cancellata all'invio. **Conservazione automatica** (`backend/retention.py`, ogni ora): richieste e appuntamenti anonimizzati dopo 24 mesi (configurabile, setting `retention_mesi`, minimo 6), chiamate/registro WhatsApp 12 mesi, visite 26 mesi. Fatture e clienti fatturati non si toccano (10 anni) |
| 5 | Statistiche e embed | ✅ | Visite anonime (hash giornaliero, nessun IP salvato). Nessun embed. Voce naturale (Vapi, USA): ora chiede conferma prima di partire e l'informativa lo dichiara |
| 6 | Sito accessibile | ✅ | axe: 0 violazioni (prima: lista dati dei contatti, regione emergenza, area tabella). Pagina `/accessibilita`. Video «La nostra storia» con sottotitoli italiani (`storia_lmc.it.vtt`) |
| 7 | Bottoni chiari | ✅ | Etichette ambigue sostituite («Prenota» → «Prenota un appuntamento», «Usa nel preventivo» → «Vai al preventivo con queste scelte», «Chiudi» ×4 → con il nome della finestra, «Invia» → «Invia il messaggio all'assistente», «Installa» → «Installa l'app»). Aree di tocco ≥ 24 px (link «Guarda la nostra storia» ora 44 px) |
| 8 | Togli recensioni finte | ✅ | Compaiono solo recensioni **approvate** dal titolare. In produzione nessun numero demo («150+ eventi») né bollino demo, nessun `aggregateRating` inventato |
| 9 | Dati professionali | — escluso | Da compilare: Admin › Testi (dati societari, P.IVA) e Fatture › Dati fiscali |
| 10 | Requisiti IT e UE | ✅ parziale | Informativa GDPR art. 13, cookie, accessibilità, intestazioni (HSTS con COOKIE_SECURE=1, Permissions-Policy). Resta a carico del titolare: dati professionali, registro dei trattamenti, nomina dei responsabili (IONOS, Twilio, Vapi, Google, provider email) e verifica finale con il consulente privacy |

## Da fare a mano (non automatizzabile)
1. **Modalità produzione**: `APP_MODE=production` sulla VPS (nasconde ogni contenuto demo). Controllabile con `deploy/verifica-online.sh`.
2. Admin › Testi: *Informativa privacy – dettagli* (`privacy_extra`) per aggiungere cose specifiche (es. DPO, sede).
3. Completa i **dati societari**.
4. Se non vuoi la «Voce naturale» di Vapi, lasciala non configurata: la chat e la voce del browser funzionano comunque.

> Questo documento è una verifica tecnica, non una consulenza legale.
