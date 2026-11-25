# Report di sicurezza – LMC Service

Data: 24/11/2026 · Ambito: codice del repository (Flask + SQLite, deploy su VPS IONOS con nginx e gunicorn).
Backup prima delle modifiche: branch git `backup-prima-logo-sicurezza`.

## Riepilogo
Nessun problema **critico**. Nessun segreto reale nel codice o nella cronologia git. Dipendenze senza vulnerabilità note.
L'app è scritta con attenzione (CSRF ovunque, query parametrizzate, upload ricodificato, token lunghi). Ho corretto 6 punti a basso rischio;
restano alcune azioni da fare **sulla VPS**, che non ho potuto controllare (non accessibile da qui).

## Cosa è stato verificato (e come)
| Controllo | Strumento | Esito |
|---|---|---|
| Dipendenze vulnerabili | `pip-audit` | nessuna vulnerabilità nota |
| Analisi del codice (SAST) | `bandit` (semgrep non installato) | 0 problemi reali; segnalazioni false: SQL costruito con nomi di colonna fissi (`metrics.py`), SHA1 usato solo per nomi file (`foto_sync.py`, `importa_social.py`), `urlopen` verso URL https fisso di Twilio |
| Segreti nel codice e nella storia git | grep su file e su tutta la cronologia (gitleaks/trufflehog non installati) | nessuna chiave reale. Unico valore trovato: `chiave-segreta-ionos-0123456789` in `tests/test_backup_cloud.py`, è un dato finto di prova |
| File sensibili tracciati da git | `git ls-files` | nessuno (`.env`, `data/`, `*.db`, `*.key`, backup sono in `.gitignore`) |
| XSS | ricerca `safe`, `innerHTML` | Jinja con escape automatico; `innerHTML` usato solo con dati propri dell'utente o del server |
| CSRF, IDOR, autorizzazioni | lettura di tutte le rotte | tutte le POST admin passano da `admin_required` + CSRF; gli appuntamenti si gestiscono con token casuale da 128 bit |
| Upload file | `media.py` | solo estensioni ammesse; le immagini sono ricodificate in WebP; i video controllano la firma `ftyp`; nomi file casuali; `/media/` ammette solo nomi esadecimali (niente path traversal) |
| Doppia prenotazione | schema DB | indice univoco `ux_slot` presente |
| Server (systemd) | `deploy/lmc.service` | utente dedicato, `NoNewPrivileges`, `ProtectSystem`, scrittura solo in `data/` e `foto/` |

Non applicabili / non controllati: Supabase, Vercel, Netlify, n8n (il progetto non li usa; non ho interrogato nessun account), la VPS reale, i log di produzione.

## Problemi trovati

### Medi
1. **Mancavano CSP e Permissions-Policy; HSTS non automatico.** → *Corretto*.
2. **Richieste pubbliche senza limite di dimensione (fino a 200 MB) né rate limit su appuntamenti e preventivi** (spam, riempimento agenda, consumo memoria). → *Corretto*.
3. **VPS: `setup-vps.sh` non configura firewall (ufw), fail2ban né blocco accesso SSH con password.** → *Lo script non lo fa, ma sulla VPS reale è già tutto attivo (verificato il 25/11/2026, vedi «Verifica della VPS» in fondo).*

### Bassi
4. Pagine admin senza `Cache-Control: no-store` (dopo il logout restavano nella cache del browser). → *Corretto*.
5. Oggetto email costruito con il nome del cliente: un a-capo nel nome faceva fallire l'invio in silenzio. → *Corretto* (oggetto su una sola riga).
6. Due prenotazioni simultanee sullo stesso orario davano errore 500 invece di un messaggio. → *Corretto* (risposta 409).
7. Blocco tentativi di login in memoria e per processo gunicorn (con 2 worker i tentativi utili diventano ~10 ogni 5 minuti). Accettabile con password lunga; migliorabile con fail2ban su nginx.
8. Backup cifrati con AES-256-CBC (`openssl enc`) senza controllo di integrità. Riservatezza ok; per l'integrità si può passare ad `age` o GPG.
9. nginx: `add_header Cache-Control` dentro `location /static/` annulla gli header di sicurezza del blocco `server` per quei file (limite noto di nginx). Effetto minimo.
10. nginx: nessun `server` predefinito che scarta gli host sconosciuti; con `TRUST_PROXY=1` l'app si fida dell'header Host per i link nelle email. Rischio basso (il link contiene un token che arriva solo al cliente stesso).

### Privacy / GDPR
- Un solo cookie tecnico di sessione, statistiche anonime (hash giornaliero con sale, nessun IP salvato): **nessun banner cookie necessario**.
- Consenso richiesto con casella obbligatoria su appuntamenti, preventivi e riepilogo chat; informativa presente.
- **Da fare**: l'informativa contiene ancora il segnaposto «[DA COMPLETARE con il consulente privacy]» (fornitori, sede dei dati, tempi di conservazione, basi giuridiche), completabile da Admin › Testi. Non esiste cancellazione automatica dei dati dei clienti vecchi (nome, telefono, email in chiaro nel database; i backup sono cifrati): conviene stabilire un tempo di conservazione (es. 24 mesi) e un modo per cancellare su richiesta.
- La cache offline (service worker) non salva né l'admin né `/api` né le pagine appuntamento: nessun dato personale offline.

## Cosa ho corretto (file modificati per la sicurezza)
- `backend/__init__.py`: header `Content-Security-Policy` (blocca plugin, `<base>` e form verso altri siti, incorniciamento; **non** limita gli script, per non rompere l'assistente vocale Vapi), `Permissions-Policy` (microfono solo al sito), `Cross-Origin-Opener-Policy`, `Strict-Transport-Security` quando `COOKIE_SECURE=1`, `no-store` su `/admin`; limite 1 MB alle richieste fuori dall'admin.
- `backend/public.py`: limite 8 richieste ogni 10 minuti per IP su appuntamenti e preventivi; prenotazione concorrente → 409.
- `backend/mailer.py`: oggetto email su una riga.

Verifica dopo le correzioni: test del progetto `test_ui` 31/31, `test_foto` 24/24, `test_e2e` 41/41, `test_team` 18/18, `test_whatsapp` 59/59, `test_social` 12/12, `test_deploy` 35/36. L'unico errore (`creati archivio dati e archivio segreti, entrambi cifrati`) c'è **anche sul codice originale** (backup cifrato con strumenti bash su Windows) e non dipende dalle modifiche. `pip-audit` ancora pulito.

## Cosa resta da fare a te
1. ~~Sulla VPS: firewall, fail2ban, SSH solo con chiave~~ → già a posto, verificato il 25/11/2026 (vedi «Verifica della VPS»).
2. Controllare nel `.env` di produzione: `APP_MODE=production`, `COOKIE_SECURE=1`, `TRUST_PROXY=1`, `ADMIN_PASSWORD` **rimossa** dopo il primo accesso, password admin cambiata (min. 10 caratteri), `SECRET_KEY` impostata o `data/secret.key` nei backup.
3. Dopo il deploy aprire il sito e controllare con https://securityheaders.com che compaiano gli header nuovi.
4. Completare l'informativa privacy e decidere i tempi di conservazione dei dati.
5. Non ho trovato chiavi esposte: **nessuna rotazione necessaria**. Se in passato hai incollato chiavi Twilio/Vapi in chat o file fuori da git, ruotale dai rispettivi pannelli.
6. Nota sul logo: i video in `app/static/media/` (loop1-3, storia_lmc.mp4) e la cartella `lmcs/` sono contenuti che non ho modificato; se contengono il vecchio logo nei fotogrammi vanno rigenerati.

## Come rifare i controlli
```
.venv\Scripts\python.exe -m pip install pip-audit bandit
.venv\Scripts\python.exe -m pip_audit -r requirements.txt
.venv\Scripts\python.exe -m bandit -q -r backend run.py -ll
set PYTHONUTF8=1 && .venv\Scripts\python.exe -m tests.test_e2e      (anche test_ui, test_whatsapp, test_team, test_foto, test_social)
git log --all -p | findstr /i "api_key secret token password"       (ricerca segreti nella storia)
```
Strumenti consigliati da aggiungere: `gitleaks detect` e `semgrep --config auto backend`.

---

## Seconda revisione (24/11/2026)
Ripetuti pip-audit (nessuna vulnerabilità), bandit (solo falsi positivi: SQL con nomi di tabella/colonna fissi, `urlopen` verso URL https fissi o configurati dall'admin, SHA1 per nomi file), ricerca segreti su tutta la cronologia (nessuno) e lettura di login, CSRF, upload, `/media`, service worker, webhook. Le correzioni del primo report sono presenti e funzionanti.

**Corretto ora (medio, a basso rischio)**
- `/admin/login` (e ogni `/admin/*`) accettava richieste fino a 200 MB anche senza accesso: ora il limite di 1 MB vale per tutti, tranne l'admin già autenticato (foto/video).
- `/api/chat` non aveva un limite per IP (costi con AI esterna, spam): ora 40 messaggi ogni 10 minuti per IP (in produzione c'è anche il limite di nginx).
- Aggiunto `tests/test_sicurezza.py` (21 controlli): header, cookie, limiti di dimensione e frequenza, CSRF, oggetto email, segreti non tracciati, service worker, logo (nessun riferimento al vecchio, nessun file mancante, manifest).

**Ancora aperto**
- Video `loop1-3.mp4` (galleria della home) e `video/*.mp4` contengono ancora il vecchio logo nei fotogrammi: vanno rigenerati.
- Host header: con `TRUST_PROXY=1` i link nelle email usano l'host ricevuto; conviene un `server` predefinito in nginx che scarta host sconosciuti (o `TRUSTED_HOSTS` in Flask).
- Informativa privacy con segnaposto: da fare. (I punti VPS del primo report risultano già a posto: vedi sotto.)

---

## Verifica della VPS (25/11/2026)
Controlli di sola lettura fatti insieme sulla VPS reale. Il primo report ipotizzava che mancassero queste protezioni, perché non potevo vederla: **sono già attive.**

| Controllo | Esito |
|---|---|
| Firewall `ufw` | attivo; aperte solo le porte previste (22, 80, 443 e quelle degli altri progetti ospitati) |
| Sito LMC (gunicorn, porta 8010) | in ascolto solo su `127.0.0.1`: si raggiunge solo da nginx |
| SSH, `sshd -T` | `passwordauthentication no`, `pubkeyauthentication yes`, `permitrootlogin without-password` |
| `fail2ban` (jail `sshd`) | attivo: 724 tentativi falliti, 57 indirizzi bloccati in totale, 15 bloccati al momento del controllo |
| Aggiornamenti di sicurezza automatici (`unattended-upgrades`) | attivo |

**Ancora aperto (basso rischio):** in nginx manca un `server` predefinito che scarta gli host sconosciuti (punto 10). Lo si può fare insieme al passaggio al dominio .it, perché nginx va comunque toccato e serve anche altri progetti sulla stessa VPS. Le altre porte aperte nel firewall (3000, 8080, 7001, 8543, 4310, 8443, 9443) non sono di LMC e non sono state toccate.
