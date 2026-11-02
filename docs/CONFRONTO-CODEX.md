# Confronto con Codex (da lanciare sul tuo computer)

Nella sessione cloud dove lavora Claude **Codex non è installato** e non c'è nessun computer collegato (Remote Control),
quindi il confronto non si può eseguire da lì. Per farlo in locale, apri questo repository con Codex (o con il tuo ciclo «claudex»)
e dagli il prompt qui sotto; poi confronta il suo elenco con `docs/CONFORMITA.md`.

## Prompt
> Sei un revisore indipendente. Analizza TUTTO il progetto (Flask + SQLite, sito vetrina PWA + gestionale admin con ruoli ADMIN/COLLABORATORE).
> Escludi i dati professionali (P.IVA, sede, IBAN). Verifica in modo adversariale, citando file:riga:
> 1. Privacy policy, cookie (solo tecnici?), informativa sui moduli, minimizzazione e conservazione dei dati (`backend/retention.py`), email ai clienti.
> 2. Statistiche anonime (`backend/metrics.py`) e assenza di embed/terze parti; voce naturale Vapi.
> 3. Accessibilità WCAG 2.2 AA (tastiera, contrasto, label, landmark, sottotitoli del video), chiarezza dei bottoni.
> 4. Recensioni solo vere (flusso `backend/reviews.py`), nessun contenuto demo in produzione.
> 5. Sicurezza: permessi per ruolo (`backend/rbac.py`: un COLLABORATORE non deve raggiungere fatture, acconti, tariffe, utenti, impostazioni), CSRF, upload, SQL injection, XSS, intestazioni HTTP, segreti, rate limit.
> 6. Correttezza: fatturazione (numerazione, IVA, acconti), concorrenza SQLite, test mancanti.
> Per ogni punto: gravità (alta/media/bassa), prova (riga di codice o comando), correzione proposta. Non modificare file.
> Poi lancia `python -m tests.test_conformita` e gli altri test in `tests/` e riporta cosa fallisce.

Quando hai il risultato incollalo qui in chat: lo confronto con il mio e applico le differenze.
