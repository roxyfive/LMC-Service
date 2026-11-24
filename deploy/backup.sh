#!/usr/bin/env bash
# =====================================================================================================
# Backup notturno LMC Service  (cron di root alle 03:20, tramite lexpro-backup-guard.sh come gli altri progetti — vedi docs/DEPLOY.md, Parte 4.9)
#   1) database SQLite (copia consistente + controllo di integrità)
#   2) data/uploads (foto e video ottimizzati) e foto/ (originali)
#   3) .env e data/secret.key
#   Tutto viene CIFRATO (AES-256) con la password in PASS_FILE: nel backup locale e nella copia sul cloud
#   non c'è mai nulla in chiaro (il database contiene anche le chiavi API inserite da Admin).
#   Poi: rotazione (ultimi KEEP_DAYS giorni), copia sul cloud (Google Drive via rclone esistente oppure IONOS S3), VERIFICA della copia
#   (presenza + dimensione + impronta) e avviso (email + WhatsApp) se qualcosa non va.
# Uso:  sudo /srv/lmc/deploy/backup.sh      Esiti:  0 ok · 1 errore · 3 copia cloud non riuscita/non verificata
# Configurazione: deploy/lmc-backup.conf (modello: lmc-backup.conf.example)
# =====================================================================================================
set -Eeuo pipefail
# shellcheck disable=SC1091
. "$(dirname "$(readlink -f "$0")")/lib-backup.sh"

STAMP="$(date +%Y%m%d_%H%M%S)"            # stesso schema degli altri backup del server: <nome>_AAAAMMGG_HHMMSS
FAIL=0
ALERTED=0
TMP=""
fail_alert() {
  [ "$ALERTED" = "1" ] && return 0; ALERTED=1
  # sotto il guard del server l'avviso (email) parte da solo perché lo script esce con codice ≠ 0: niente doppioni
  if [ "$VIA_GUARD" = "1" ]; then LOG "AVVISO (lo invia il guard): $1 – $2"; else send_alert "$1" "$2"; fi
}
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
  DATA_FILE="$BACKUP_DIR/lmc_$STAMP.tar.gz.enc"
  tar -czf - -C "$STAGE" . | enc_stream > "$DATA_FILE"
  dec_stream < "$DATA_FILE" | tar -tzf - >/dev/null          # prova: si decifra e si legge
else
  DATA_FILE="$BACKUP_DIR/lmc_$STAMP.tar.gz"
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
    SEC_FILE="$BACKUP_DIR/lmc_secrets_$STAMP.tar.gz.enc"
    tar -czf - -C "$SEC" . | enc_stream > "$SEC_FILE"
    dec_stream < "$SEC_FILE" | tar -tzf - >/dev/null
    LOG "backup segreti (.env, secret.key) cifrato ok: $(basename "$SEC_FILE")"
  else
    LOG "ATTENZIONE: nessuna password di cifratura: .env NON salvato (mai in chiaro)."
    FAIL=1
  fi
fi

# --- rotazione locale ---
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'lmc_*' -o -name 'lmc-data-*' -o -name 'lmc-secrets-*' \) -mtime +$((KEEP_DAYS - 1)) -delete

# --- 4) copia sul cloud + verifica ---
REMOTE_STATE="non configurata"
if [ -n "$REMOTE" ]; then
  if ! command -v rclone >/dev/null 2>&1; then
    LOG "ERRORE: rclone non installato (apt install rclone)"; REMOTE_STATE="ERRORE"; FAIL=3
    fail_alert "Backup: copia $CLOUD_LABEL non riuscita" "rclone non è installato sul server."
  elif rclone copy "$BACKUP_DIR" "$REMOTE" "${BK_INCLUDE[@]}" "${RC_OPTS[@]}" ; then
    BAD=0
    for f in "$DATA_FILE" ${SEC_FILE:+"$SEC_FILE"}; do verify_remote_file "$f" || BAD=1; done
    if [ "$BAD" = "0" ]; then
      rclone delete "$REMOTE" "${BK_INCLUDE[@]}" --min-age "${REMOTE_KEEP_DAYS}d" "${RC_OPTS[@]}" || LOG "ATTENZIONE: pulizia dei vecchi backup sul cloud non riuscita"
      REMOTE_STATE="ok e verificata"
      LOG "copia su $CLOUD_LABEL ok e verificata: $([ -n "$S3_BUCKET" ] && echo "$S3_BUCKET/$S3_PREFIX" || echo "$REMOTE")"
    else
      REMOTE_STATE="ERRORE di verifica"; FAIL=3
      fail_alert "Backup: copia su $CLOUD_LABEL NON verificata" "Il file non risulta integro sul cloud $CLOUD_LABEL (vedi /var/log/lmc-backup.log). Il backup locale è stato fatto."
    fi
  else
    REMOTE_STATE="ERRORE"; FAIL=3
    LOG "ERRORE: copia su $CLOUD_LABEL non riuscita (chiavi, endpoint, bucket o rete)"
    fail_alert "Backup: copia su $CLOUD_LABEL NON riuscita" "Impossibile copiare il backup sul cloud $CLOUD_LABEL (controlla la configurazione in deploy/lmc-backup.conf, il remote rclone e la rete)."
  fi
fi

# --- 5) segno l'ultimo backup riuscito (lo legge backup-status.sh) ---
if [ "$FAIL" = "0" ]; then
  printf 'time=%s\nstamp=%s\ndata=%s\ncloud=%s\n' "$(date -Is)" "$STAMP" "$(basename "$DATA_FILE")" "$REMOTE_STATE" > "$BACKUP_DIR/LAST_OK"
  # copia dello stato (nessun segreto) nella cartella dati: la pagina Admin › Backup la legge senza accedere a /root
  cp "$BACKUP_DIR/LAST_OK" "$APP_DIR/data/backup-status.txt" 2>/dev/null && chmod 644 "$APP_DIR/data/backup-status.txt" && { id "$APP_USER" >/dev/null 2>&1 && chown "$APP_USER" "$APP_DIR/data/backup-status.txt" 2>/dev/null || true; }
fi
KEPT="$(find "$BACKUP_DIR" -maxdepth 1 \( -name 'lmc_2*' -o -name 'lmc-data-*' \) | wc -l)"
if [ "$FAIL" = "0" ]; then LOG "Backup LMC OK: $DATA_FILE ($(du -h "$DATA_FILE" | cut -f1)) · segreti: ${SEC_FILE:+ok} · cloud: $REMOTE_STATE · copie locali: $KEEP_DAYS giorni ($KEPT file)"
else LOG "Backup LMC CON ERRORI (exit $FAIL): $DATA_FILE · cloud: $REMOTE_STATE"; fi
exit "$FAIL"
