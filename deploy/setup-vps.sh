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
[ -n "$DOMAIN" ] || { echo "Uso: bash $0 DOMINIO EMAIL   (es. bash $0 www.lmcservice.it pasquale@email.it)"; echo "     oppure, senza dominio ancora:  bash $0 IP_DELLA_VPS   (sito in HTTP; il dominio si collega dopo con deploy/collega-dominio.sh)"; exit 1; }
# se al posto del dominio c'è un indirizzo IP: installazione senza HTTPS (Let's Encrypt non emette certificati per un IP)
IPMODE=0; echo "$DOMAIN" | grep -Eq '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' && IPMODE=1
[ "$IPMODE" = "1" ] || [ -n "$EMAIL" ] || { echo "Per il dominio serve anche l'email per il certificato HTTPS:  bash $0 $DOMAIN tua@email.it"; exit 1; }
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
  [ -n "$EMAIL" ] && sed -i "s|^OWNER_EMAIL=.*|OWNER_EMAIL=$EMAIL|" "$APP/.env"
  [ "$IPMODE" = "1" ] && sed -i "s|^COOKIE_SECURE=.*|COOKIE_SECURE=0|" "$APP/.env"
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
if [ "$IPMODE" = "1" ]; then sed "s/DOMINIO/_/g" "$APP/deploy/nginx-lmc.conf" > /etc/nginx/sites-available/lmc; else sed "s/DOMINIO/$DOMAIN/g" "$APP/deploy/nginx-lmc.conf" > /etc/nginx/sites-available/lmc; fi
ln -sf /etc/nginx/sites-available/lmc /etc/nginx/sites-enabled/lmc
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "== 7/8 Certificato HTTPS (Let's Encrypt)"
if [ "$IPMODE" = "1" ]; then
  echo "   Installazione con IP: HTTPS saltato. Quando hai il dominio:  bash $APP/deploy/collega-dominio.sh DOMINIO EMAIL"
elif certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect; then
  echo "   HTTPS attivo."
else
  echo "   ATTENZIONE: certbot non è riuscito (il DNS del dominio punta già a questa VPS? porte 80/443 aperte nel firewall IONOS?)."
  echo "   Sistema e rilancia:  certbot --nginx -d $DOMAIN -m $EMAIL --agree-tos --redirect"
fi

echo "== 8/8 Backup notturno"
[ -s /root/.lmc-backup-pass ] || { python3 -c 'import secrets;print(secrets.token_urlsafe(32))' > /root/.lmc-backup-pass; chmod 600 /root/.lmc-backup-pass; NEWPASS=1; }
chmod +x "$APP"/deploy/*.sh
# configurazione del backup (qui vanno, in seguito, le chiavi IONOS): file escluso da git, leggibile solo da root
[ -f "$APP/deploy/lmc-backup.conf" ] || cp "$APP/deploy/lmc-backup.conf.example" "$APP/deploy/lmc-backup.conf"
chown root:root "$APP/deploy/lmc-backup.conf"; chmod 600 "$APP/deploy/lmc-backup.conf"
cp "$APP/deploy/lmc-backup.cron" /etc/cron.d/lmc-backup
chmod 644 /etc/cron.d/lmc-backup
mkdir -p /var/backups/lmc && chmod 700 /var/backups/lmc
cat > /etc/logrotate.d/lmc-backup <<'LR'
/var/log/lmc-backup.log {
    monthly
    rotate 6
    compress
    missingok
    notifempty
}
LR
"$APP/deploy/backup.sh" || true
systemctl restart lmc

echo
echo "=========================== FATTO ==========================="
if [ "$IPMODE" = "1" ]; then SCHEMA=http; else SCHEMA=https; fi
echo "Sito:   $SCHEMA://$DOMAIN        Admin: $SCHEMA://$DOMAIN/admin        Controllo: $SCHEMA://$DOMAIN/health"
[ "$IPMODE" = "1" ] && echo "(in HTTP microfono e installazione come app non funzionano: collega il dominio appena possibile)"
echo "Controllo completo:  bash $APP/deploy/verifica-online.sh $SCHEMA://$DOMAIN"
if [ -n "$FIRST_PASS" ]; then
  echo "Utente admin: admin    Password INIZIALE: $FIRST_PASS   (annotala ORA; cambiala subito da Admin > Cambia password)"
fi
if [ "${NEWPASS:-0}" = "1" ]; then
  echo "Password di cifratura dei backup (.env cifrato): $(cat /root/.lmc-backup-pass)"
  echo "  -> copiala in un posto sicuro FUORI dal VPS (gestore password): senza non si recupera il .env dai backup."
fi
echo "Backup notturno: ogni giorno alle 03:30 in /var/backups/lmc (7 giorni, tutto cifrato). Controllo alle 08:00: se manca un backup arriva un avviso."
echo "Copia su IONOS Object Storage: NON ancora attiva. Compila le chiavi in $APP/deploy/lmc-backup.conf (guida: docs/DEPLOY.md, Parte 4.3)."
echo "Stato dei backup in qualsiasi momento:  sudo $APP/deploy/backup-status.sh"
