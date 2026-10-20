#!/usr/bin/env bash
# =====================================================================================================
# Backup notturno LMC Service  (cron: ogni notte alle 03:30 — vedi deploy/lmc-backup.cron)
#   1) database SQLite (copia consistente + controllo di integrità)
#   2) data/uploads (foto e video ottimizzati) e foto/ (originali)
#   3) .env e data/secret.key
#   Tutto viene CIFRATO (AES-256) con la password in PASS_FILE: nel backup locale e nella copia su IONOS
#   non c'è mai nulla in chiaro (il database contiene anche le chiavi API inserite da Admin).
#   Poi: rotazione (ultimi KEEP_DAYS giorni), copia su IONOS Object Storage, VERIFICA della copia
#   (presenza + dimensione + impronta) e avviso (email + WhatsApp) se qualcosa non va.
# Uso:  sudo /srv/lmc/deploy/backup.sh      Esiti:  0 ok · 1 errore · 3 copia cloud non riuscita/non verificata
# Configurazione: deploy/lmc-backup.conf (modello: lmc-backup.conf.example)
# =====================================================================================================
set -Eeuo pipefail
# shellcheck disable=SC1091
. "$(dirname "$(readlink -f "$0")")/lib-backup.sh"

STAMP="$(date +%Y-%m-%d_%H%M)"
FAIL=0
ALERTED=0
TMP=""
fail_alert() { [ "$ALERTED" = "1" ] && return 0; ALERTED=1; send_alert "$1" "$2"; }
cleanup() { [ -n "$TMP" ] && rm -rf "$TMP"; true; }
on_error() { LOG "ERRORE inatteso alla riga $1"; fail_alert "Backup NON riuscito" "Errore inatteso durante il backup notturno (riga $1). Il sito non è stato toccato."; exit 1; }
trap cleanup EXIT
trap 'on_error $LINENO' ERR

mkdir -p "$BACKUP_DIR"; chmod 700 "$BACKUP_DIR"
exec 9>"$BACKUP_DIR/.lock"
flock -n 9 || { LOG "un altro backup è già in corso: esco"; exit 0; }
conf_warn_permissions

[ -d "$APP_DIR/data" ] || { LOG "ERRORE: $APP_DIR/data non esiste (APP_DIR sbagliata?)"; fail_alert "Backup NON riuscito" "Cartella dati non trovata: $APP_DIR/data"; exit 1; }
[ -f "$APP_DIR/data/lmc.db" ] || { LOG "ERRORE: database non trovato"; fail_alert "Backup NON riuscito" "Database non trovato in $APP_DIR/data"; exit 1; }
if [ "$ENCRYPT" = "1" ] && ! need_pass; then
  LOG "ERRORE: manca la password di cifratura ($PASS_FILE): senza non salvo nulla (mai dati in chiaro)."
  fail_alert "Backup NON riuscito" "Manca la password di cifratura dei backup ($PASS_FILE)."
  exit 1
fi
cloud_setup || true
if [ -n "$REMOTE" ] && [ "$ENCRYPT" != "1" ]; then
  LOG "ERRORE: la copia cloud richiede ENCRYPT=1: nel cloud non va mai nulla in chiaro."
  fail_alert "Backup NON riuscito" "Configurazione non sicura: copia cloud attiva con ENCRYPT=0."
  exit 1
fi

TMP="$(mktemp -d)"; chmod 711 "$TMP"

# --- 1) database: copia consistente anche mentre il sito è in uso (WAL), eseguita come utente del sito ---
mkdir -p "$TMP/db"; chmod 700 "$TMP/db"
[ "$(id -u)" = "0" ] && id "$APP_USER" >/dev/null 2>&1 && [ -z "${LMC_NO_RUNUSER:-}" ] && chown "$APP_USER" "$TMP/db"
as_app_user python3 - "$APP_DIR/data/lmc.db" "$TMP/db/lmc.db" <<'PY'
import sqlite3, sys
src = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True, timeout=30); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
PY
CHECK="$(python3 - "$TMP/db/lmc.db" <<'PY'
import sqlite3, sys
print(sqlite3.connect(sys.argv[1]).execute("PRAGMA integrity_check").fetchone()[0])
PY
)"
[ "$CHECK" = "ok" ] || { LOG "ERRORE: il database copiato non è integro ($CHECK)"; fail_alert "Backup NON riuscito" "Il database non ha superato il controllo di integrità: $CHECK"; exit 1; }

# --- 2) contenuti ---
STAGE="$TMP/stage"; mkdir -p "$STAGE"
mv "$TMP/db/lmc.db" "$STAGE/lmc.db"
[ -d "$APP_DIR/data/uploads" ] && cp -a "$APP_DIR/data/uploads" "$STAGE/uploads"
[ -d "$APP_DIR/foto" ] && cp -a "$APP_DIR/foto" "$STAGE/foto"
if [ "$ENCRYPT" = "1" ]; then
  DATA_FILE="$BACKUP_DIR/lmc-data-$STAMP.tar.gz.enc"
  tar -czf - -C "$STAGE" . | enc_stream > "$DATA_FILE"
  dec_stream < "$DATA_FILE" | tar -tzf - >/dev/null          # prova: si decifra e si legge
else
  DATA_FILE="$BACKUP_DIR/lmc-data-$STAMP.tar.gz"
  tar -czf "$DATA_FILE" -C "$STAGE" .
  tar -tzf "$DATA_FILE" >/dev/null
fi
LOG "backup dati ok: $(basename "$DATA_FILE") ($(du -h "$DATA_FILE" | cut -f1))"

# --- 3) segreti (.env + secret.key): sempre cifrati ---
SEC="$TMP/secrets"; mkdir -p "$SEC"
[ -f "$APP_DIR/.env" ] && cp -a "$APP_DIR/.env" "$SEC/.env"
[ -f "$APP_DIR/data/secret.key" ] && cp -a "$APP_DIR/data/secret.key" "$SEC/secret.key"
SEC_FILE=""
if [ -n "$(ls -A "$SEC" 2>/dev/null)" ]; then
  if need_pass; then
    SEC_FILE="$BACKUP_DIR/lmc-secrets-$STAMP.tar.gz.enc"
    tar -czf - -C "$SEC" . | enc_stream > "$SEC_FILE"
    dec_stream < "$SEC_FILE" | tar -tzf - >/dev/null
    LOG "backup segreti (.env, secret.key) cifrato ok: $(basename "$SEC_FILE")"
  else
    LOG "ATTENZIONE: nessuna password di cifratura: .env NON salvato (mai in chiaro)."
    FAIL=1
  fi
fi

# --- rotazione locale ---
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'lmc-data-*' -o -name 'lmc-secrets-*' \) -mtime +$((KEEP_DAYS - 1)) -delete

# --- 4) copia su IONOS Object Storage + verifica ---
REMOTE_STATE="non configurata"
if [ -n "$REMOTE" ]; then
  if ! command -v rclone >/dev/null 2>&1; then
    LOG "ERRORE: rclone non installato (apt install rclone)"; REMOTE_STATE="ERRORE"; FAIL=3
    fail_alert "Backup: copia IONOS non riuscita" "rclone non è installato sul server."
  elif rclone copy "$BACKUP_DIR" "$REMOTE" --include 'lmc-*' "${RC_OPTS[@]}" ; then
    BAD=0
    for f in "$DATA_FILE" ${SEC_FILE:+"$SEC_FILE"}; do verify_remote_file "$f" || BAD=1; done
    if [ "$BAD" = "0" ]; then
      rclone delete "$REMOTE" --include 'lmc-*' --min-age "${REMOTE_KEEP_DAYS}d" "${RC_OPTS[@]}" || LOG "ATTENZIONE: pulizia dei vecchi backup sul cloud non riuscita"
      REMOTE_STATE="ok e verificata"
      LOG "copia su IONOS ok e verificata: $S3_BUCKET/${S3_PREFIX}"
    else
      REMOTE_STATE="ERRORE di verifica"; FAIL=3
      fail_alert "Backup: copia su IONOS NON verificata" "Il file non risulta integro sul cloud IONOS (vedi /var/log/lmc-backup.log). Il backup locale è stato fatto."
    fi
  else
    REMOTE_STATE="ERRORE"; FAIL=3
    LOG "ERRORE: copia su IONOS non riuscita (chiavi, endpoint, bucket o rete)"
    fail_alert "Backup: copia su IONOS NON riuscita" "Impossibile copiare il backup su IONOS Object Storage (controlla chiavi, endpoint e bucket in deploy/lmc-backup.conf)."
  fi
fi

# --- 5) segno l'ultimo backup riuscito (lo legge backup-status.sh) ---
if [ "$FAIL" = "0" ]; then
  printf 'time=%s\nstamp=%s\ndata=%s\ncloud=%s\n' "$(date -Is)" "$STAMP" "$(basename "$DATA_FILE")" "$REMOTE_STATE" > "$BACKUP_DIR/LAST_OK"
fi
LOG "backup terminato — locale: ok · cloud: $REMOTE_STATE · giorni conservati: $(find "$BACKUP_DIR" -maxdepth 1 -name 'lmc-data-*' | wc -l)"
exit "$FAIL"
