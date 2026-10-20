#!/usr/bin/env bash
# =====================================================================================================
# Backup notturno LMC Service
#   1) database SQLite (copia consistente + controllo integrità)
#   2) cartelle: data/uploads (foto/video caricati e ottimizzati) e foto/ (originali)
#   3) .env e data/secret.key CIFRATI (AES-256) in un file a parte
#   Rotazione: tiene gli ultimi KEEP_DAYS giorni (default 7). Copia opzionale fuori dal VPS con rclone.
# Uso: sudo /srv/lmc/deploy/backup.sh      (lo lancia il cron ogni notte, vedi deploy/lmc-backup.cron)
# Configurazione facoltativa in /etc/lmc-backup.conf (vedi deploy/lmc-backup.conf.example)
# =====================================================================================================
set -Eeuo pipefail
umask 077

CONF="${LMC_BACKUP_CONF:-/etc/lmc-backup.conf}"
# shellcheck disable=SC1090
[ -f "$CONF" ] && . "$CONF"
: "${APP_DIR:=/srv/lmc}"
: "${BACKUP_DIR:=/var/backups/lmc}"
: "${KEEP_DAYS:=7}"
: "${PASS_FILE:=/root/.lmc-backup-pass}"
: "${RCLONE_REMOTE:=}"          # es. ionos:lmc-backup  (vuoto = nessuna copia fuori dal VPS)
STAMP="$(date +%Y-%m-%d_%H%M)"
LOG() { echo "$(date -Is) $*"; }
FAIL=0

[ -d "$APP_DIR/data" ] || { LOG "ERRORE: $APP_DIR/data non esiste (APP_DIR sbagliata?)"; exit 1; }
[ -f "$APP_DIR/data/lmc.db" ] || { LOG "ERRORE: database $APP_DIR/data/lmc.db non trovato"; exit 1; }
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- 1) database: copia consistente anche mentre il sito è in uso (modalità WAL) ---
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$APP_DIR/data/lmc.db" ".backup '$TMP/lmc.db'"
else
  python3 - "$APP_DIR/data/lmc.db" "$TMP/lmc.db" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
PY
fi
CHECK="$(python3 - "$TMP/lmc.db" <<'PY'
import sqlite3, sys
print(sqlite3.connect(sys.argv[1]).execute("PRAGMA integrity_check").fetchone()[0])
PY
)"
[ "$CHECK" = "ok" ] || { LOG "ERRORE: il database copiato non è integro ($CHECK)"; exit 1; }

# --- 2) foto e video ---
[ -d "$APP_DIR/data/uploads" ] && cp -a "$APP_DIR/data/uploads" "$TMP/uploads"
[ -d "$APP_DIR/foto" ] && cp -a "$APP_DIR/foto" "$TMP/foto"
DATA_FILE="$BACKUP_DIR/lmc-data-$STAMP.tar.gz"
tar -czf "$DATA_FILE" -C "$TMP" .
tar -tzf "$DATA_FILE" >/dev/null          # verifica che l'archivio si legga
LOG "backup dati ok: $(basename "$DATA_FILE") ($(du -h "$DATA_FILE" | cut -f1))"

# --- 3) segreti (.env + secret.key) SEMPRE cifrati ---
SEC="$TMP/secrets"; mkdir -p "$SEC"
[ -f "$APP_DIR/.env" ] && cp -a "$APP_DIR/.env" "$SEC/.env"
[ -f "$APP_DIR/data/secret.key" ] && cp -a "$APP_DIR/data/secret.key" "$SEC/secret.key"
if [ -n "$(ls -A "$SEC" 2>/dev/null)" ]; then
  if [ -s "$PASS_FILE" ]; then
    SEC_FILE="$BACKUP_DIR/lmc-secrets-$STAMP.tar.gz.enc"
    tar -czf - -C "$SEC" . | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass "file:$PASS_FILE" -out "$SEC_FILE"
    LOG "backup segreti cifrato ok: $(basename "$SEC_FILE")"
  else
    LOG "ATTENZIONE: manca la password di cifratura ($PASS_FILE): .env NON salvato (mai in chiaro). Crea il file e rilancia."
    FAIL=2
  fi
fi

# --- rotazione: via i backup più vecchi di KEEP_DAYS giorni ---
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'lmc-data-*.tar.gz' -o -name 'lmc-secrets-*.enc' \) -mtime +$((KEEP_DAYS - 1)) -delete

# --- copia fuori dal VPS (facoltativa) ---
if [ -n "$RCLONE_REMOTE" ]; then
  if command -v rclone >/dev/null 2>&1; then
    if rclone sync "$BACKUP_DIR" "$RCLONE_REMOTE" --include 'lmc-*' --quiet; then
      LOG "copia remota ok: $RCLONE_REMOTE"
    else
      LOG "ERRORE: copia remota su $RCLONE_REMOTE non riuscita"; FAIL=3
    fi
  else
    LOG "ATTENZIONE: RCLONE_REMOTE impostato ma rclone non è installato (sudo apt install rclone)"; FAIL=3
  fi
fi

LOG "backup terminato (conservati: $(find "$BACKUP_DIR" -maxdepth 1 -name 'lmc-data-*.tar.gz' | wc -l) giorni di dati)"
exit "$FAIL"
