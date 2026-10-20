#!/usr/bin/env bash
# Ripristino da backup LMC Service.
# Uso:  sudo /srv/lmc/deploy/restore.sh /var/backups/lmc/lmc-data-AAAA-MM-GG_HHMM.tar.gz [lmc-secrets-....enc]
# Ferma il sito, tiene una copia di sicurezza dello stato attuale (data.prima-del-ripristino-...), ripristina, riavvia.
set -Eeuo pipefail
umask 077
: "${APP_DIR:=/srv/lmc}"
: "${PASS_FILE:=/root/.lmc-backup-pass}"
: "${SERVICE:=lmc}"
DATA_ARCHIVE="${1:-}"; SEC_ARCHIVE="${2:-}"
[ -f "$DATA_ARCHIVE" ] || { echo "Uso: $0 <lmc-data-....tar.gz> [lmc-secrets-....enc]"; exit 1; }
echo "ATTENZIONE: sostituirò database e foto con quelli del backup:"
echo "  $DATA_ARCHIVE"
[ -n "$SEC_ARCHIVE" ] && echo "  e .env/secret.key da $SEC_ARCHIVE"
if [ "${LMC_YES:-}" != "1" ]; then read -r -p "Scrivi SI per continuare: " A; [ "$A" = "SI" ] || { echo "Annullato."; exit 1; }; fi

STAMP="$(date +%Y%m%d_%H%M%S)"
systemctl stop "$SERVICE" 2>/dev/null || true
[ -d "$APP_DIR/data" ] && mv "$APP_DIR/data" "$APP_DIR/data.prima-del-ripristino-$STAMP"
[ -d "$APP_DIR/foto" ] && mv "$APP_DIR/foto" "$APP_DIR/foto.prima-del-ripristino-$STAMP"
mkdir -p "$APP_DIR/data"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
tar -xzf "$DATA_ARCHIVE" -C "$TMP"
mv "$TMP/lmc.db" "$APP_DIR/data/lmc.db"
[ -d "$TMP/uploads" ] && mv "$TMP/uploads" "$APP_DIR/data/uploads"
if [ -d "$TMP/foto" ]; then mv "$TMP/foto" "$APP_DIR/foto"; else mkdir -p "$APP_DIR/foto"; fi
if [ -n "$SEC_ARCHIVE" ]; then
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$PASS_FILE" -in "$SEC_ARCHIVE" | tar -xzf - -C "$TMP"
  [ -f "$TMP/.env" ] && cp -a "$TMP/.env" "$APP_DIR/.env"
  [ -f "$TMP/secret.key" ] && cp -a "$TMP/secret.key" "$APP_DIR/data/secret.key"
fi
chmod 600 "$APP_DIR/.env" "$APP_DIR/data/lmc.db" "$APP_DIR/data/secret.key" 2>/dev/null || true
chown -R lmc:lmc "$APP_DIR/data" "$APP_DIR/foto" 2>/dev/null || true
systemctl start "$SERVICE" 2>/dev/null || true
echo "Ripristino completato. Lo stato precedente è in $APP_DIR/data.prima-del-ripristino-$STAMP"
