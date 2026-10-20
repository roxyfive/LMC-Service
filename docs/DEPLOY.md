# Guida di deploy – LMC Service su VPS Ubuntu IONOS

Pensata per chi non è esperto di server (i nomi delle voci nel pannello IONOS possono variare leggermente nel tempo). Si copia e incolla un comando alla volta. Ogni passo dice **cosa fa** e **come capire che è andato bene**.
Tempo previsto: 30–45 minuti (più l'attesa del DNS).

> **Cosa installi:** il sito (Python + gunicorn) gestito da *systemd* (riparte da solo), **nginx** davanti (compressione, cache, upload, limiti anti-abuso), **HTTPS** gratuito con Let's Encrypt, **backup notturno** con rotazione di 7 giorni, controllo di salute `/health`.
> I file di configurazione sono nella cartella `deploy/` del progetto: `lmc.service`, `nginx-lmc.conf`, `lmc-proxy.conf`, `env.production.example`, `backup.sh`, `restore.sh`, `lmc-backup.cron`, `setup-vps.sh`.

---

## Parte 1 – Preparazione (sul pannello IONOS e sul tuo PC)

### 1.1 Crea/avvia la VPS
Nel **Cloud Panel IONOS** (cloud.ionos.it): *Server e Cloud › Server › VPS*. Scegli **Ubuntu 22.04 o 24.04**. Con 1 vCore / 1–2 GB di RAM il sito va bene.
Annota l'**indirizzo IP** e la **password di root** (o carica la tua chiave SSH).

### 1.2 Firewall della VPS
Nel Cloud Panel apri la VPS › **Rete › Criteri firewall** e consenti in ingresso: **22** (SSH), **80** (HTTP), **443** (HTTPS). Senza 80/443 il certificato HTTPS non si crea.

### 1.3 Dominio (DNS)
Nel pannello **Domini** IONOS, per il tuo dominio (es. `lmcservice.it`) crea:
- record **A** con nome `@` (e uno per `www`) → **IP della VPS**
- (se la VPS ha IPv6) record **AAAA** → indirizzo IPv6.

Il DNS può impiegare da pochi minuti a qualche ora. Controllo dal tuo PC: `ping www.tuodominio.it` deve mostrare l'IP della VPS.

### 1.4 Collegati alla VPS
Da **Windows** apri *PowerShell*, da Mac/Linux il *Terminale*:
```bash
ssh root@IP_DELLA_VPS
```
(la prima volta rispondi `yes`; poi incolla la password). Se compare un prompt tipo `root@...:~#` sei dentro.

---

## Parte 2 – Installazione automatica (consigliata)

### 2.1 Copia il progetto sulla VPS
**Opzione A – con git** (se il progetto è su GitHub e hai accesso):
```bash
apt update && apt install -y git
git clone https://github.com/roxyfive/lmc-service.git /srv/lmc
```
**Opzione B – dal tuo PC** (cartella del progetto, *senza* la cartella `data/`):
```bash
# da PowerShell sul PC, dentro la cartella LMC-Service:
scp -r app backend contenuti deploy docs foto logo tests video run.py requirements.txt importa_social.py root@IP_DELLA_VPS:/srv/lmc/
```
(prima, sulla VPS: `mkdir -p /srv/lmc`).

### 2.2 Lancia l'installatore
Sostituisci dominio ed email (l'email serve a Let's Encrypt per avvisarti se il certificato sta per scadere):
```bash
bash /srv/lmc/deploy/setup-vps.sh www.tuodominio.it tua@email.it
```
Lo script fa, in ordine: installa i pacchetti · imposta il fuso orario Europe/Rome · crea l'utente di servizio `lmc` · crea l'ambiente Python · crea il file `.env` di **produzione** con chiave segreta casuale e una password admin iniziale · avvia il servizio e verifica `/health` · configura nginx · richiede il certificato HTTPS · attiva il backup notturno e ne esegue uno subito.
Può essere rilanciato senza danni (non cancella dati, non rigenera un `.env` esistente).

**A fine esecuzione leggi con attenzione il riquadro «FATTO»**: contiene
- l'indirizzo del sito e dell'admin;
- la **password admin iniziale** → annotala e cambiala subito;
- la **password di cifratura dei backup** → salvala in un gestore di password *fuori dalla VPS*.

### 2.3 Controlli veloci
```bash
systemctl status lmc --no-pager        # deve dire: active (running)
curl -s https://www.tuodominio.it/health   # deve rispondere {"db":"ok","mode":"production","status":"ok"}
```
Poi dal browser: `https://www.tuodominio.it` (sito) e `/admin` (pannello). Sul lucchetto deve esserci HTTPS valido.

### 2.4 Primi passi nel pannello
1. **Admin › 🔐 Cambia password.**
2. Compila i dati mancanti seguendo `docs/CHECKLIST-GO-LIVE.md`.
3. **Email in uscita (SMTP)**: modifica `/srv/lmc/.env` (vedi sotto «Modificare la configurazione») e riavvia.

---

## Parte 3 – Installazione manuale (alternativa, passo per passo)
Se preferisci non usare lo script. Come utente `root`.

```bash
# 1. pacchetti e fuso orario
apt update && apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx sqlite3 openssl rclone cron curl
timedatectl set-timezone Europe/Rome

# 2. utente di servizio e ambiente Python (il progetto è già in /srv/lmc)
useradd --system --home /srv/lmc --shell /usr/sbin/nologin lmc
cd /srv/lmc && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p data foto/organizzate

# 3. configurazione
cp deploy/env.production.example .env
python3 -c "import secrets;print(secrets.token_hex(32))"     # copia l'output in SECRET_KEY=
python3 -c "import secrets;print(secrets.token_urlsafe(12))"  # copia l'output in ADMIN_PASSWORD= (solo primo avvio)
nano .env                       # imposta SECRET_KEY, ADMIN_PASSWORD, OWNER_EMAIL, SMTP_*   (Ctrl+O salva, Ctrl+X esce)
chown -R lmc:lmc data foto .env && chmod 600 .env

# 4. servizio
cp deploy/lmc.service /etc/systemd/system/lmc.service
systemctl daemon-reload && systemctl enable --now lmc
curl http://127.0.0.1:8010/health            # deve rispondere status ok
sed -i '/^ADMIN_PASSWORD=/d' .env && chown lmc:lmc .env && chmod 600 .env   # la password iniziale non serve più nel file

# 5. nginx (sostituisci DOMINIO)
cp deploy/lmc-proxy.conf /etc/nginx/lmc-proxy.conf
sed "s/DOMINIO/www.tuodominio.it/g" deploy/nginx-lmc.conf > /etc/nginx/sites-available/lmc
ln -sf /etc/nginx/sites-available/lmc /etc/nginx/sites-enabled/lmc && rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 6. HTTPS
certbot --nginx -d www.tuodominio.it -m tua@email.it --agree-tos --redirect
certbot renew --dry-run                      # prova del rinnovo automatico

# 7. backup notturno
python3 -c "import secrets;print(secrets.token_urlsafe(32))" > /root/.lmc-backup-pass && chmod 600 /root/.lmc-backup-pass
cat /root/.lmc-backup-pass                   # SALVA questa password in un gestore di password fuori dal VPS
cp deploy/lmc-backup.cron /etc/cron.d/lmc-backup && chmod 644 /etc/cron.d/lmc-backup
mkdir -p /var/backups/lmc && chmod 700 /var/backups/lmc
chmod +x deploy/backup.sh deploy/restore.sh && deploy/backup.sh
```
Le impostazioni di nginx incluse: compressione **gzip**, cache dei file statici (7 giorni; 30 per audio/video dell'intro), **upload fino a 200 MB** (foto e video dall'admin), limiti anti-abuso su `/api/` e `/webhook/`, endpoint `/health` senza log.

**HSTS (facoltativo, dopo aver verificato che l'HTTPS funziona):** nel blocco `server` con `listen 443` aggiungi
`add_header Strict-Transport-Security "max-age=31536000" always;` e `nginx -t && systemctl reload nginx`.

---

## Parte 4 – Backup

### 4.1 Cosa fa il backup notturno (ogni notte alle 03:30)
Script: `/srv/lmc/deploy/backup.sh`, avviato da `/etc/cron.d/lmc-backup`. Salva in **`/var/backups/lmc`** (cartella riservata, permessi 700):
| File | Contenuto |
|---|---|
| `lmc-data-AAAA-MM-GG_HHMM.tar.gz` | **database** (copia consistente + controllo di integrità), **`data/uploads`** (foto/video ottimizzati), **`foto/`** (originali) |
| `lmc-secrets-AAAA-MM-GG_HHMM.tar.gz.enc` | **`.env` e `secret.key` CIFRATI** (AES-256) con la password in `/root/.lmc-backup-pass` — mai in chiaro |

**Rotazione:** vengono tenuti gli ultimi **7 giorni**; i più vecchi si cancellano da soli (cambia `KEEP_DAYS` in `/etc/lmc-backup.conf`, modello in `deploy/lmc-backup.conf.example`).
Esito nel log: `tail -n 20 /var/log/lmc-backup.log`. Prova manuale: `sudo /srv/lmc/deploy/backup.sh`.
Se manca la password di cifratura lo script **non salva mai il `.env` in chiaro** e termina con avviso.

### 4.2 Scaricare il backup sul tuo PC (copia fuori dal VPS)
Un backup che sta solo sul server non protegge dalla perdita del server. Da **PowerShell/Terminale sul tuo PC**:
```bash
scp root@IP_DELLA_VPS:/var/backups/lmc/lmc-*  C:\backup-lmc\          # Windows: cartella a tua scelta
# oppure, scarica solo l'ultimo giorno:
scp "root@IP_DELLA_VPS:/var/backups/lmc/lmc-*$(date +%F)*" ./         # Mac/Linux
```
Con **WinSCP** o **FileZilla** (protocollo SFTP, host = IP, utente `root`) puoi anche trascinare i file dalla cartella `/var/backups/lmc`. Fallo almeno una volta a settimana.

### 4.3 Copia automatica su IONOS Object Storage (S3)
1. Cloud Panel IONOS › **Storage › Object Storage**: crea una chiave di accesso (*Access key* + *Secret key*) e un **bucket** (es. `lmc-backup`). Annota l'**endpoint** della regione del bucket (es. `s3-eu-central-1.ionoscloud.com`; è scritto nel pannello).
2. Sulla VPS (`rclone` è già installato dallo script):
```bash
rclone config
```
   Rispondi: `n` (new remote) · nome `ionos` · storage `s3` · provider `IONOS Cloud` · `access_key_id` e `secret_access_key` copiati dal pannello · region/endpoint come da pannello · il resto invio.
   Prova: `rclone lsd ionos:` deve elencare il bucket.
3. Attiva la copia notturna: crea `/etc/lmc-backup.conf` (modello in `deploy/lmc-backup.conf.example`) con
```
RCLONE_REMOTE=ionos:lmc-backup/lmc
```
   Da quella notte `backup.sh` copia anche lì (e mantiene la stessa rotazione dei 7 giorni). Se la copia fallisce lo script lo scrive nel log.
> Nota: la copia remota è una **sincronizzazione** della cartella dei backup: cancellando un file locale per rotazione sparisce anche dal bucket. Usa un bucket/cartella dedicato.

### 4.4 Ripristino (se qualcosa va storto)
```bash
ls /var/backups/lmc                                     # scegli i file della data che vuoi
sudo /srv/lmc/deploy/restore.sh /var/backups/lmc/lmc-data-AAAA-MM-GG_HHMM.tar.gz  /var/backups/lmc/lmc-secrets-AAAA-MM-GG_HHMM.tar.gz.enc
```
Lo script chiede conferma (scrivi `SI`), **ferma il sito**, conserva lo stato attuale in `data.prima-del-ripristino-…`, ripristina database/foto/(.env), imposta i permessi e **riavvia**. Il secondo file (segreti) è facoltativo. Per ripristinare su un server nuovo: installa con `setup-vps.sh`, copia i file di backup in `/var/backups/lmc` e lancia `restore.sh`; la password di cifratura (`/root/.lmc-backup-pass`) deve essere la stessa usata per il backup.
**Prova il ripristino almeno una volta** prima del go-live.

---

## Parte 5 – Uso quotidiano

| Cosa | Comando |
|---|---|
| Il sito è su? | `curl -s https://DOMINIO/health` (o monitora con UptimeRobot ogni 5 min) |
| Stato del servizio | `systemctl status lmc --no-pager` |
| Log del sito (errori, avvisi di avvio) | `journalctl -u lmc -n 100 --no-pager` · in diretta: `journalctl -u lmc -f` |
| Riavviare | `systemctl restart lmc` |
| Log di nginx | `tail -n 50 /var/log/nginx/error.log` |
| Modificare la configurazione | `nano /srv/lmc/.env` → salva → `systemctl restart lmc` |
| Aggiornare il sito (git) | `cd /srv/lmc && git pull && .venv/bin/pip install -r requirements.txt && systemctl restart lmc` (**prima fai un backup**: `deploy/backup.sh`) |
| Aggiornare (copia file) | ricopia le cartelle con `scp` come in 2.1 **senza** `data/`, poi `systemctl restart lmc` |
| Spazio su disco | `df -h /` · `du -sh /srv/lmc/data /var/backups/lmc` |

Il nuovo avvio mostra nel log eventuali **avvisi di configurazione** (es. `COOKIE_SECURE=1 mancante`): `journalctl -u lmc -n 30 | grep ATTENZIONE`.

### Report e promemoria
Di default il sito li invia da solo (thread interno, senza duplicati con più worker). In alternativa, per un controllo più preciso: `LMC_NO_BG=1` nel `.env` e in `/etc/cron.d/lmc-tempi`:
```
* * * * *  lmc  cd /srv/lmc && .venv/bin/python run.py --report     >> /var/log/lmc-report.log 2>&1
0 * * * *  lmc  cd /srv/lmc && .venv/bin/python run.py --promemoria >> /var/log/lmc-promemoria.log 2>&1
```

---

## Parte 6 – Sicurezza: cosa è già a posto e cosa tocca a te
- **Segreti fuori da git:** `.env`, `data/`, chiavi, database e backup sono nel `.gitignore`; il repository non contiene chiavi (verificato dai test). `.env` ha permessi `600` e appartiene all'utente `lmc`.
- **Chiavi API (Twilio, Vapi):** si inseriscono da *Admin › Impostazioni*; stanno nel database (che è nel backup) e non vengono mai rimostrate.
- **Il servizio gira senza privilegi** (utente `lmc`, può scrivere solo in `data/` e `foto/`).
- **Admin:** password personale (≥10 caratteri), blocco dopo 5 tentativi, cookie sicuro con HTTPS, `robots.txt` esclude `/admin`.
- **Tocca a te:** cambiare la password admin, salvare la password dei backup fuori dal VPS, tenere aggiornato Ubuntu (`apt update && apt upgrade -y` ogni tanto, poi riavvio se richiesto), ruotare le chiavi API se un file di backup esce dal tuo controllo.
- **Webhook Vapi** (`/webhook/vapi`): pubblico ma protetto dal secret nell'header `X-Vapi-Secret` e dal limite di richieste di nginx.

## Parte 7 – Problemi comuni
| Sintomo | Causa probabile | Cosa fare |
|---|---|---|
| `certbot` fallisce | DNS non ancora aggiornato o porta 80/443 chiusa | Controlla `ping DOMINIO`, firewall IONOS (1.2), poi `certbot --nginx -d DOMINIO -m EMAIL --agree-tos --redirect` |
| 502 Bad Gateway | il servizio è fermo | `systemctl status lmc`, `journalctl -u lmc -n 50` |
| Non riesco a entrare nell'admin | password dimenticata | `cd /srv/lmc && sudo -u lmc .venv/bin/python -c "from backend import create_app; from backend.db import ex; from werkzeug.security import generate_password_hash as g; create_app().app_context().push(); ex('UPDATE admin_users SET pw_hash=? WHERE username=?',(g('NuovaPasswordTemporanea1'),'admin'))"` poi cambiala dal pannello |
| Upload di un video fallisce | file oltre 60 MB o richiesta oltre 200 MB | comprimi il video, carica un file alla volta |
| Le email non arrivano | SMTP non configurato | guarda `data/outbox.log` e imposta `SMTP_*` nel `.env` |
| Microfono/PWA non funzionano | sito su http | serve HTTPS (Parte 2/3) |
| Il sito mostra «DEMO» | `APP_MODE` non è `production` | correggi `.env` e riavvia |

## Appendice – installazione in locale (per prove)
```bash
python -m venv .venv && .venv\Scripts\activate    # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python run.py            # http://localhost:5000  —  admin: /admin
```
Per provare il server di produzione in locale: `APP_MODE=production gunicorn run:app -b 127.0.0.1:8010`.
