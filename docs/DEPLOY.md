# Guida di deploy – LMC Service su VPS Ubuntu IONOS

Pensata per chi non è esperto di server (i nomi delle voci nel pannello IONOS possono variare leggermente nel tempo). Si copia e incolla un comando alla volta. Ogni passo dice **cosa fa** e **come capire che è andato bene**.
Tempo previsto: 30–45 minuti (più l'attesa del DNS).

> **Cosa installi:** il sito (Python + gunicorn) gestito da *systemd* (riparte da solo), **nginx** davanti (compressione, cache, upload, limiti anti-abuso), **HTTPS** gratuito con Let's Encrypt, **backup notturno** con rotazione di 7 giorni, controllo di salute `/health`.
> I file di configurazione sono nella cartella `deploy/` del progetto: `lmc.service`, `nginx-lmc.conf`, `lmc-proxy.conf`, `env.production.example`, `setup-vps.sh`, e per i backup `backup.sh`, `restore.sh`, `backup-status.sh`, `backup-alert.py`, `lib-backup.sh`, `lmc-backup.conf.example`, `lmc-backup.cron`.

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

### 1.5 Controllo preliminare della VPS (consigliato)
Prima di installare, lancia sulla VPS il controllo che non modifica nulla (sistema, RAM, disco, porte 22/80/443 libere, firewall, DNS del dominio):
```bash
bash /srv/lmc/deploy/verifica-vps.sh www.tuodominio.it      # senza dominio: bash /srv/lmc/deploy/verifica-vps.sh
```
Le porte aperte **sul firewall IONOS** si controllano dal tuo PC (`Test-NetConnection IP -Port 80` in PowerShell, `nc -vz IP 80` su Mac/Linux): lo script ti ricorda i comandi.

### 1.6 Non hai ancora il dominio?
Installa con l'**IP** della VPS: `bash /srv/lmc/deploy/setup-vps.sh IP_DELLA_VPS` (sito in **HTTP**; microfono, PWA e installazione come app richiedono HTTPS e quindi non funzionano finché non colleghi il dominio). Quando il DNS punta alla VPS: `bash /srv/lmc/deploy/collega-dominio.sh www.tuodominio.it tua@email.it` (configura nginx, certificato HTTPS e cookie sicuri).

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
Lo script fa, in ordine: installa i pacchetti · imposta il fuso orario Europe/Rome · crea l'utente di servizio `lmc` · crea l'ambiente Python · crea il file `.env` di **produzione** con chiave segreta casuale e una password admin iniziale · avvia il servizio e verifica `/health` · configura nginx · richiede il certificato HTTPS · attiva il backup notturno cifrato (con controllo mattutino) e ne esegue uno subito. La copia su IONOS Object Storage si attiva dopo, con le chiavi (Parte 4.3).
Può essere rilanciato senza danni (non cancella dati, non rigenera un `.env` esistente).

**A fine esecuzione leggi con attenzione il riquadro «FATTO»**: contiene
- l'indirizzo del sito e dell'admin;
- la **password admin iniziale** → annotala e cambiala subito;
- la **password di cifratura dei backup** → salvala in un gestore di password *fuori dalla VPS*.

### 2.3 Controlli (uno script fa tutto)
```bash
bash /srv/lmc/deploy/verifica-online.sh https://www.tuodominio.it
```
Controlla servizi, permessi del `.env`, `/health` in modalità production, nessun bollino DEMO, certificato HTTPS, redirect, gzip, log senza errori, backup. Manualmente:
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

# 7. backup notturno (dettagli e copia su IONOS: Parte 4)
python3 -c "import secrets;print(secrets.token_urlsafe(32))" > /root/.lmc-backup-pass && chmod 600 /root/.lmc-backup-pass
cat /root/.lmc-backup-pass                   # SALVA questa password in un gestore di password fuori dal VPS
cp deploy/lmc-backup.conf.example deploy/lmc-backup.conf && chmod 600 deploy/lmc-backup.conf
cp deploy/lmc-backup.cron /etc/cron.d/lmc-backup && chmod 644 /etc/cron.d/lmc-backup
mkdir -p /var/backups/lmc && chmod 700 /var/backups/lmc
chmod +x deploy/*.sh && deploy/backup.sh
```
Le impostazioni di nginx incluse: compressione **gzip**, cache dei file statici (7 giorni; 30 per audio/video dell'intro), **upload fino a 200 MB** (foto e video dall'admin), limiti anti-abuso su `/api/` e `/webhook/`, endpoint `/health` senza log.

**HSTS (facoltativo, dopo aver verificato che l'HTTPS funziona):** nel blocco `server` con `listen 443` aggiungi
`add_header Strict-Transport-Security "max-age=31536000" always;` e `nginx -t && systemctl reload nginx`.

---

## Parte 4 – Sistema di backup (notturno + copia su IONOS)

### 4.0 In breve: cosa succede ogni notte
| Ora | Cosa | Dove finiscono i file |
|---|---|---|
| **03:30** | `deploy/backup.sh` (lo lancia `cron`): copia consistente del **database** + controllo di integrità, **foto/video** (`data/uploads` e `foto/`), **`.env` e `secret.key`** | `/var/backups/lmc/` sul server |
| subito dopo | tutto viene **cifrato** (AES-256) con la password in `/root/.lmc-backup-pass` e riletto per prova | `lmc-data-AAAA-MM-GG_HHMM.tar.gz.enc` e `lmc-secrets-AAAA-MM-GG_HHMM.tar.gz.enc` |
| subito dopo | **rotazione**: si cancellano i backup più vecchi di 7 giorni (locale **e** cloud) | – |
| subito dopo | **copia su IONOS Object Storage** (se configurata, 4.3) e **verifica**: file presente, stessa dimensione, stessa impronta md5 (o confronto byte per byte) | bucket IONOS, cartella `lmc/` |
| se qualcosa fallisce | **avviso** via email al titolare (`OWNER_EMAIL`) e WhatsApp a chi è «di turno» | – |
| **08:00** | `backup-status.sh --check --alert`: se nelle ultime 26 ore non risulta nessun backup riuscito (es. il server era spento), **avviso** | – |

> **Sicurezza:** nei file di backup, **anche quelli sul cloud, non c'è nulla in chiaro**: né il `.env`, né il database (che contiene anche le chiavi API inserite da Admin). Senza la password di cifratura i file sono illeggibili — per questo **la password va conservata fuori dal VPS** (4.1). Le **chiavi di IONOS** stanno solo in `deploy/lmc-backup.conf`, file escluso da git (4.5).

### 4.1 Prima cosa: salva la password di cifratura
L'installer la crea in `/root/.lmc-backup-pass` e la mostra una volta a fine installazione. Rileggila quando vuoi:
```bash
sudo cat /root/.lmc-backup-pass
```
Copiala in un **gestore di password** (o stampala e conservala in cassaforte). **Se la perdi, i backup non si possono più aprire.**

### 4.2 Verificare e modificare la pianificazione sul VPS
Il backup è un compito di `cron` definito in **`/etc/cron.d/lmc-backup`**:
```
30 3 * * * root /srv/lmc/deploy/backup.sh >> /var/log/lmc-backup.log 2>&1
0  8 * * * root /srv/lmc/deploy/backup-status.sh --check --alert >> /var/log/lmc-backup.log 2>&1
```
(minuto · ora · giorno · mese · giorno-settimana · utente · comando → **03:30 ogni notte**; il fuso orario del server è Europe/Rome, impostato dall'installer).

| Cosa vuoi fare | Comando |
|---|---|
| Vedere la pianificazione | `cat /etc/cron.d/lmc-backup` |
| Cron è attivo? | `systemctl status cron --no-pager` (deve essere *active (running)*) |
| Il fuso orario è giusto? | `timedatectl` (deve mostrare *Europe/Rome*); se no: `sudo timedatectl set-timezone Europe/Rome` |
| Vedere che cron l'ha lanciato | `grep lmc-backup /var/log/syslog \| tail` (oppure `journalctl -u cron \| grep lmc`) |
| Leggere il log dei backup | `tail -n 40 /var/log/lmc-backup.log` — ogni notte ci sono righe «backup dati ok», «copia su IONOS ok e verificata», «backup terminato» |
| **Stato completo** (ultimo riuscito, file locali e sul cloud) | `sudo /srv/lmc/deploy/backup-status.sh` |
| Lanciarlo subito a mano | `sudo /srv/lmc/deploy/backup.sh` |
| Cambiare l'orario | `sudo nano /etc/cron.d/lmc-backup` → cambia `30 3` (es. `0 2` = le 02:00) → salva (Ctrl+O, Invio, Ctrl+X). Cron rilegge il file da solo |
| Cambiare la rotazione | in `deploy/lmc-backup.conf`: `KEEP_DAYS=7` (locale) e `REMOTE_KEEP_DAYS=7` (cloud) |

**Rotazione dei 7 giorni:** ogni notte vengono cancellati i file `lmc-data-*`/`lmc-secrets-*` più vecchi di 7 giorni, quindi restano le ultime **7 notti**. Spazio occupato: `du -sh /var/backups/lmc`.
**Esiti dello script:** `0` tutto ok · `1` errore (nessun backup salvato) · `3` backup locale ok ma copia IONOS non riuscita/non verificata.

### 4.3 Copia su IONOS Object Storage (S3) – passo per passo
**A) Crea il bucket e le chiavi nel pannello IONOS** (i nomi delle voci possono variare leggermente):
1. Accedi al **Cloud Panel / Data Center Designer** IONOS → menu **Storage → Object Storage** (S3).
2. **Crea un bucket**: nome in minuscolo, univoco in tutto IONOS (es. `lmc-service-backup-7f3k`); scegli la **regione** vicina (Frankfurt, Berlino o Logroño) e lasciala **privata**. *Non attivare «Object Lock»* (impedirebbe la rotazione automatica).
3. **Annota l'endpoint** della regione: nel pannello accanto al bucket (esempi: `s3-eu-central-1.ionoscloud.com` Frankfurt · `s3-eu-central-2.ionoscloud.com` Berlino · `s3-eu-south-2.ionoscloud.com` Logroño).
4. Apri **Key management** (Gestione chiavi) → **Generate key / Genera chiave**: ottieni **Access key** e **Secret key**. La *Secret key* si vede **una sola volta**: copiala subito.

**B) Inserisci le chiavi sul VPS** (l'installer ha già creato il file; se manca: `cp /srv/lmc/deploy/lmc-backup.conf.example /srv/lmc/deploy/lmc-backup.conf`):
```bash
sudo nano /srv/lmc/deploy/lmc-backup.conf
sudo chmod 600 /srv/lmc/deploy/lmc-backup.conf      # leggibile solo da root
```
Compila queste righe (il resto lascialo com'è):
```
S3_ENDPOINT=s3-eu-central-1.ionoscloud.com      # l'endpoint annotato, senza https://
S3_ACCESS_KEY=la-tua-access-key
S3_SECRET_KEY=la-tua-secret-key
S3_BUCKET=lmc-service-backup-7f3k
S3_PREFIX=lmc                                  # cartella dentro il bucket (si crea da sola)
S3_REGION=                                     # solo se dà errore di regione (es. de, eu-central-2, eu-south-2)
```
Serve `rclone` (l'installer lo mette): `rclone version`. Se è molto vecchio (< 1.55) aggiornalo: `curl https://rclone.org/install.sh | sudo bash`.
> Non occorre `rclone config`: le chiavi vengono passate a rclone da `backup.sh` ogni volta, senza scriverle altrove.

**C) Prova la copia** (subito, senza aspettare la notte):
```bash
sudo /srv/lmc/deploy/backup.sh
```
Cerca nell'output queste righe: **«verifica cloud ok: lmc-data-… (… byte, controllo: md5)»** (una per i dati, una per i segreti) e **«copia su IONOS ok e verificata»**. Poi controlla:
```bash
sudo /srv/lmc/deploy/backup-status.sh        # mostra i file locali e quelli sul cloud IONOS
```
e nel pannello IONOS, dentro il bucket, deve comparire la cartella `lmc/` con i due file `.enc`.
Se compare **ERRORE**: «Access Denied/InvalidAccessKey» → chiavi sbagliate o incollate con uno spazio; «NoSuchBucket» → nome del bucket; «no such host/timeout» → endpoint sbagliato (controlla la regione) o firewall in uscita; «SignatureDoesNotMatch» → Secret key errata (rigenerala).

### 4.4 Verifica automatica della copia e avvisi
Dopo ogni caricamento `backup.sh` **controlla che il file sia davvero su IONOS**:
1. il file **c'è** sul bucket;
2. ha **esattamente la stessa dimensione** del file locale;
3. ha la stessa **impronta md5**; se il cloud non la fornisce (caricamenti a blocchi) scarica il file e lo **confronta byte per byte**. Con `VERIFY_DOWNLOAD=1` in `lmc-backup.conf` questo confronto è sempre byte per byte.

Se un controllo fallisce (o la copia non parte) lo script **esce con codice 3, non aggiorna «ultimo backup riuscito» e manda un avviso**: email a `OWNER_EMAIL` (serve SMTP nel `.env`) e WhatsApp a chi è «di turno» (serve Twilio configurato). Il backup **locale** resta comunque valido. Controllo manuale in qualsiasi momento: `sudo /srv/lmc/deploy/backup-status.sh --verify-remote` (e `VERIFY_DOWNLOAD=1 sudo …` per il confronto completo).

### 4.5 Sicurezza delle chiavi e dei dati
- **Cifratura obbligatoria:** `backup.sh` rifiuta di partire senza la password di cifratura e **rifiuta di copiare sul cloud con `ENCRYPT=0`**. Tutto ciò che arriva su IONOS è illeggibile senza la password (AES-256, PBKDF2).
- **`.env` e `secret.key`** sono in un file cifrato a parte (`lmc-secrets-…`); il database (che contiene anche le chiavi Twilio/Vapi di Admin) e le foto sono nel file `lmc-data-…`, anch'esso cifrato.
- **Le chiavi IONOS non finiscono su git:** vivono solo in `deploy/lmc-backup.conf` (o `/etc/lmc-backup.conf`), file **escluso dal `.gitignore`** e con permessi 600 (lo script avvisa se sono più larghi). Nel repository c'è solo il modello `lmc-backup.conf.example`, senza valori. Le chiavi non compaiono nei log.
- Consigli: usa per il backup una chiave IONOS dedicata (revocabile senza toccare altro); se sospetti che un file di backup o la chiave siano usciti dal tuo controllo, **rigenera la chiave IONOS** e, se serve, cambia anche le chiavi API (Twilio/Vapi).

### 4.6 Scaricare i backup sul PC (copia di sicurezza in più)
```bash
scp root@IP_DELLA_VPS:/var/backups/lmc/lmc-*  C:\backup-lmc\        # Windows (PowerShell)
```
Oppure con **WinSCP/FileZilla** (SFTP, host = IP, utente `root`): cartella `/var/backups/lmc`. I file sono cifrati: per aprirli serve la password del punto 4.1.

### 4.7 Ripristino
**Prima di tutto**, per sicurezza: ogni ripristino **ferma il sito**, **conserva lo stato attuale** in `data.prima-del-ripristino-…`, controlla il backup **prima** di toccare qualcosa (se la password è sbagliata o il file è rovinato si ferma senza modificare nulla) e poi **riavvia**.

**a) Da un backup sul server** (`/var/backups/lmc`):
```bash
ls /var/backups/lmc                                      # scegli la data
sudo /srv/lmc/deploy/restore.sh /var/backups/lmc/lmc-data-AAAA-MM-GG_HHMM.tar.gz.enc
# aggiungi il file dei segreti SOLO se vuoi ripristinare anche .env e secret.key:
sudo /srv/lmc/deploy/restore.sh /var/backups/lmc/lmc-data-….tar.gz.enc /var/backups/lmc/lmc-secrets-….tar.gz.enc
```
**b) Da IONOS Object Storage** (anche su un server nuovo, dopo `setup-vps.sh`):
```bash
sudo /srv/lmc/deploy/restore.sh --cloud-list             # elenca i backup sul cloud (dimensione, data, nome)
sudo /srv/lmc/deploy/restore.sh --from-cloud latest      # scarica (controllando le impronte) e ripristina l'ULTIMO
sudo /srv/lmc/deploy/restore.sh --from-cloud 2026-10-21_0330   # una data precisa
sudo /srv/lmc/deploy/restore.sh --from-cloud latest --with-env # ripristina anche .env e secret.key (disastro: server nuovo)
```
Ti chiede conferma: scrivi **SI**. A fine ripristino:
```bash
curl -s https://DOMINIO/health             # deve dire status ok
journalctl -u lmc -n 30 --no-pager         # nessun errore
```
**Server nuovo, da zero:** 1) installa con `setup-vps.sh` · 2) rimetti **la stessa password di cifratura** in `/root/.lmc-backup-pass` (`nano`, poi `chmod 600`) · 3) compila `deploy/lmc-backup.conf` con le chiavi IONOS · 4) `restore.sh --from-cloud latest --with-env`.
**Prova il ripristino almeno una volta prima del go-live** (anche su una VPS di prova).

### 4.8 Problemi comuni dei backup
| Sintomo | Cosa fare |
|---|---|
| «manca la password di cifratura» | `ls -l /root/.lmc-backup-pass` deve esistere (permessi 600); se l'hai persa e hai una copia, rimettila; altrimenti i vecchi backup non sono recuperabili: creane una nuova (`python3 -c "import secrets;print(secrets.token_urlsafe(32))" > /root/.lmc-backup-pass; chmod 600 …`) e fai subito un nuovo backup |
| Arriva l'avviso delle 08:00 «Backup notturno MANCANTE» | `tail -n 50 /var/log/lmc-backup.log`; `systemctl status cron`; spazio disco `df -h /`; lancia `sudo deploy/backup.sh` a mano |
| «copia su IONOS NON riuscita» | vedi 4.3-C (chiavi/endpoint/bucket); `sudo deploy/backup-status.sh` per vedere cosa c'è sul cloud |
| Disco pieno | riduci `KEEP_DAYS`, sposta i video grandi, o allarga il disco dal Cloud Panel IONOS |
| Nessuna email di avviso | imposta `SMTP_*` e `OWNER_EMAIL` nel `.env`; per WhatsApp configura Twilio (Admin › Impostazioni) |

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
| Stato dei backup (locale + IONOS) | `sudo /srv/lmc/deploy/backup-status.sh` |

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
