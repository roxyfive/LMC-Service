# Guida di deploy – VPS Ubuntu (Nginx + Gunicorn + systemd + SSL + backup)

> Tutti i comandi vanno eseguiti **sul tuo VPS**. Questa guida non modifica nulla da sola.
> Sostituisci `lmc.tuodominio.it` con il dominio reale e `deploy` con il tuo utente.

## 0. Prerequisiti
- VPS Ubuntu 22.04/24.04 con accesso SSH, dominio con record **A** verso l'IP del VPS.
- Firewall: porte 22, 80, 443 aperte.

## 1. Pacchetti
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx sqlite3
```

## 2. Copia del progetto
```bash
sudo mkdir -p /srv/lmc && sudo chown $USER:$USER /srv/lmc
# dal tuo PC (PowerShell):  scp -r LMC-Service/* utente@IP_VPS:/srv/lmc/
cd /srv/lmc
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
Non copiare la cartella `data/` del PC (database/foto di prova) se vuoi partire puliti.

## 3. Configurazione (.env)
```bash
cp .env.example .env && nano .env
```
Imposta almeno:
- `APP_MODE=production` (dati reali; `demo` = dati finti per mostrarlo a Pasquale)
- `SECRET_KEY=` stringa lunga casuale (`python3 -c "import secrets;print(secrets.token_hex(32))"`)
- `ADMIN_USER` e `ADMIN_PASSWORD` (usata **solo al primo avvio** per creare l'hash; poi **cancella la riga**)
- `OWNER_EMAIL` e i dati `SMTP_*` per le email
- (opzionale) `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` per l'assistente AI (proxy già presente sul VPS)
```bash
chmod 600 .env
```
Se non imposti ADMIN_PASSWORD, al primo avvio la password viene generata e stampata una volta nel log.

## 4. Servizio systemd (Gunicorn)
Crea `/etc/systemd/system/lmc.service`:
```ini
[Unit]
Description=LMC Service (Gunicorn)
After=network.target

[Service]
User=deploy
WorkingDirectory=/srv/lmc
EnvironmentFile=/srv/lmc/.env
ExecStart=/srv/lmc/.venv/bin/gunicorn -w 2 -b 127.0.0.1:8010 "run:app"
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now lmc
sudo systemctl status lmc      # deve essere "active (running)"
journalctl -u lmc -n 50        # log (qui compare l'eventuale password admin generata)
```
> I promemoria non si duplicano anche con 2 worker (flag `reminded` nel database).

## 5. Nginx
Crea `/etc/nginx/sites-available/lmc`:
```nginx
server {
    server_name lmc.tuodominio.it;
    client_max_body_size 80M;          # upload foto/video

    location /static/ { alias /srv/lmc/app/static/; expires 7d; }
    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/lmc /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 6. Certificato SSL (HTTPS)
```bash
sudo certbot --nginx -d lmc.tuodominio.it
sudo certbot renew --dry-run     # verifica il rinnovo automatico
```
Dopo l'HTTPS la PWA è installabile dai telefoni.

## 7. Backup giornaliero (database + foto)
Copia `docs/deploy/backup.sh` in `/srv/lmc/backup.sh`, poi:
```bash
chmod +x /srv/lmc/backup.sh
sudo mkdir -p /var/backups/lmc && sudo chown $USER /var/backups/lmc
crontab -e
```
Aggiungi:
```
30 3 * * *  /srv/lmc/backup.sh >> /var/log/lmc-backup.log 2>&1
0 18 * * *  cd /srv/lmc && .venv/bin/python run.py --promemoria
```
La prima riga fa il backup alle 03:30 (tiene 14 giorni); la seconda invia i promemoria degli appuntamenti di domani.
Ripristino: ferma il servizio, estrai l'archivio in `/srv/lmc/data/`, riavvia.
Consiglio: copia periodicamente `/var/backups/lmc` fuori dal VPS (rsync/scp).

## 8. Aggiornamenti futuri
```bash
cd /srv/lmc && git pull   # oppure ricopia i file
.venv/bin/pip install -r requirements.txt
sudo systemctl restart lmc
```

## 9. Assistente telefonico AI (predisposto, spento)
Per attivarlo in futuro: `PHONE_AI_ENABLED=1` e `PHONE_WEBHOOK_TOKEN=<token lungo>` in `.env`, poi punta il tuo provider voce a
`POST https://lmc.tuodominio.it/webhook/telefono` con header `X-Webhook-Token` e JSON `{"from":"+39...","transcript":"..."}`.
Le chiamate compaiono in Admin → Chiamate (AI).
