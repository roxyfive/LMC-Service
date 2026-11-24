#!/usr/bin/env bash
# =====================================================================================================
# Collega un DOMINIO a un sito già installato con il solo IP (nginx + certificato HTTPS + cookie sicuri).
# Prima: record DNS A del dominio → IP della VPS.   Uso (root):  bash /srv/lmc/deploy/collega-dominio.sh www.dominio.it tua@email.it
# =====================================================================================================
set -Eeuo pipefail
DOMAIN="${1:-}"; EMAIL="${2:-}"; APP=/srv/lmc
[ "$(id -u)" = "0" ] && [ -n "$DOMAIN" ] && [ -n "$EMAIL" ] || { echo "Uso (come root): bash $0 DOMINIO EMAIL"; exit 1; }
sed "s/DOMINIO/$DOMAIN/g" "$APP/deploy/nginx-lmc.conf" > /etc/nginx/sites-available/lmc
ln -sf /etc/nginx/sites-available/lmc /etc/nginx/sites-enabled/lmc
nginx -t && systemctl reload nginx
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
sed -i 's/^COOKIE_SECURE=.*/COOKIE_SECURE=1/' "$APP/.env"
chown lmc:lmc "$APP/.env"; chmod 600 "$APP/.env"
systemctl restart lmc
echo "Fatto: https://$DOMAIN — ora imposta il dominio in Admin › Testi › «Sito ufficiale – URL» e controlla:  bash $APP/deploy/verifica-online.sh https://$DOMAIN"
