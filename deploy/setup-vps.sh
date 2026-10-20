#!/usr/bin/env bash
# =====================================================================================================
# Installazione guidata di LMC Service su una VPS Ubuntu 22.04/24.04 (IONOS).
# Prima di lanciarlo: 1) il progetto è copiato in /srv/lmc   2) il record DNS "A" del dominio punta all'IP della VPS
# Uso (come root):   bash /srv/lmc/deploy/setup-vps.sh  www.tuodominio.it  tua@email.it
# Si può rilanciare senza danni (non cancella dati, non rigenera il .env se esiste già).
# =====================================================================================================
set -Eeuo pipefail
DOMAIN="${1:-}"; EMAIL="${2:-}"
[ "$(id -u)" = "0" ] || { echo "Lancialo come root (sudo -i)."; exit 1; }
[ -n "$DOMAIN" ] && [ -n "$EMAIL" ] || { echo "Uso: bash $0 DOMINIO EMAIL   (es. bash $0 www.lmcservice.it pasquale@email.it)"; exit 1; }
APP=/srv/lmc
[ -f "$APP/run.py" ] || { echo "Non trovo $APP/run.py: copia prima il progetto in $APP."; exit 1; }

echo "== 1/8 Pacchetti di sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx sqlite3 openssl rclone cron curl
timedatectl set-timezone Europe/Rome || true

echo "== 2/8 Utente di servizio 'lmc' (senza login)"
id lmc >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin lmc
mkdir -p "$APP/data" "$APP/foto/organizzate"

echo "== 3/8 Ambiente Python"
[ -d "$APP/.venv" ] || python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install --quiet --upgrade pip
"$APP/.venv/bin/pip" install --quiet -r "$APP/requirements.txt"

echo "== 4/8 Configurazione (.env)"
FIRST_PASS=""
if [ ! -f "$APP/.env" ]; then
  cp "$APP/deploy/env.production.example" "$APP/.env"
  SK="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"
  FIRST_PASS="$(python3 -c 'import secrets;print(secrets.token_urlsafe(12))')"
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SK|; s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$FIRST_PASS|; s|^PORT=.*|PORT=8010|" "$APP/.env"
  grep -q '^OWNER_EMAIL=' "$APP/.env" && sed -i "s|^OWNER_EMAIL=.*|OWNER_EMAIL=$EMAIL|" "$APP/.env"
else
  echo "   .env già presente: non lo tocco."
fi
chown -R lmc:lmc "$APP/data" "$APP/foto" "$APP/.env"
chmod 600 "$APP/.env"

echo "== 5/8 Servizio systemd"
cp "$APP/deploy/lmc.service" /etc/systemd/system/lmc.service
systemctl daemon-reload
systemctl enable --now lmc
sleep 4
curl -fsS http://127.0.0.1:8010/health && echo "   gunicorn risponde." || { echo "Il servizio non risponde: guarda  journalctl -u lmc -n 50"; exit 1; }
# la password iniziale serve solo al primo avvio: ora si toglie dal file
sed -i '/^ADMIN_PASSWORD=/d' "$APP/.env"
chown lmc:lmc "$APP/.env"; chmod 600 "$APP/.env"

echo "== 6/8 Nginx"
cp "$APP/deploy/lmc-proxy.conf" /etc/nginx/lmc-proxy.conf
sed "s/DOMINIO/$DOMAIN/g" "$APP/deploy/nginx-lmc.conf" > /etc/nginx/sites-available/lmc
ln -sf /etc/nginx/sites-available/lmc /etc/nginx/sites-enabled/lmc
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "== 7/8 Certificato HTTPS (Let's Encrypt)"
if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect; then
  echo "   HTTPS attivo."
else
  echo "   ATTENZIONE: certbot non è riuscito (il DNS del dominio punta già a questa VPS? porte 80/443 aperte nel firewall IONOS?)."
  echo "   Sistema e rilancia:  certbot --nginx -d $DOMAIN -m $EMAIL --agree-tos --redirect"
fi

echo "== 8/8 Backup notturno"
[ -s /root/.lmc-backup-pass ] || { python3 -c 'import secrets;print(secrets.token_urlsafe(32))' > /root/.lmc-backup-pass; chmod 600 /root/.lmc-backup-pass; NEWPASS=1; }
cp "$APP/deploy/lmc-backup.cron" /etc/cron.d/lmc-backup
chmod 644 /etc/cron.d/lmc-backup
chmod +x "$APP/deploy/backup.sh" "$APP/deploy/restore.sh"
mkdir -p /var/backups/lmc && chmod 700 /var/backups/lmc
"$APP/deploy/backup.sh" || true
systemctl restart lmc

echo
echo "=========================== FATTO ==========================="
echo "Sito:   https://$DOMAIN        Admin: https://$DOMAIN/admin        Controllo: https://$DOMAIN/health"
if [ -n "$FIRST_PASS" ]; then
  echo "Utente admin: admin    Password INIZIALE: $FIRST_PASS   (annotala ORA; cambiala subito da Admin > Cambia password)"
fi
if [ "${NEWPASS:-0}" = "1" ]; then
  echo "Password di cifratura dei backup (.env cifrato): $(cat /root/.lmc-backup-pass)"
  echo "  -> copiala in un posto sicuro FUORI dal VPS (gestore password): senza non si recupera il .env dai backup."
fi
echo "Backup notturno: ogni giorno alle 03:30 in /var/backups/lmc (7 giorni)."
