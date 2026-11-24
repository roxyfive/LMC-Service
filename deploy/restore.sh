#!/usr/bin/env bash
# =====================================================================================================
# Ripristino LMC Service da un backup locale o da IONOS Object Storage.
#   Da file locale :  sudo restore.sh /root/backups_lmc/lmc_AAAAMMGG_HHMMSS.tar.gz.enc [lmc_secrets_....tar.gz.enc]
#   Dal cloud IONOS:  sudo restore.sh --cloud-list                      (elenca i backup sul cloud)
#                     sudo restore.sh --from-cloud latest               (scarica e ripristina l'ultimo)
#                     sudo restore.sh --from-cloud 20261021_032001 [--with-env]   (una data precisa; --with-env ripristina anche .env e secret.key)
# Ferma il sito, conserva lo stato attuale (data.prima-del-ripristino-…), ripristina, riavvia.
# La password di cifratura (PASS_FILE) deve essere quella usata per il backup. Ogni passo è spiegato in docs/DEPLOY.md.
# =====================================================================================================
set -Eeuo pipefail
# shellcheck disable=SC1091
. "$(dirname "$(readlink -f "$0")")/lib-backup.sh"
: "${SERVICE:=lmc}"

MODE="local"; WHICH="latest"; WITH_ENV=0; POS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --cloud-list) MODE="list" ;;
    --from-cloud) MODE="cloud"; if [ -n "${2:-}" ] && [ "${2#--}" = "$2" ]; then WHICH="$2"; shift; fi ;;
    --with-env) WITH_ENV=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) POS+=("$1") ;;
  esac
  shift
done

TMP="$(mktemp -d)"; chmod 711 "$TMP"; trap 'rm -rf "$TMP"' EXIT

if [ "$MODE" = "list" ] || [ "$MODE" = "cloud" ]; then
  cloud_setup || { LOG "ERRORE: la copia cloud non è configurata (chiavi S3 in deploy/lmc-backup.conf)."; exit 1; }
  command -v rclone >/dev/null || { LOG "ERRORE: rclone non installato (apt install rclone)"; exit 1; }
fi
if [ "$MODE" = "list" ]; then
  echo "Backup su $REMOTE (dimensione · data · nome):"
  rclone lsl "$REMOTE" "${BK_INCLUDE[@]}" "${RC_OPTS[@]}" | sort -k4 | awk '{printf "%12d byte  %s %s  %s\n",$1,$2,substr($3,1,8),$4}'
  exit 0
fi

if [ "$MODE" = "cloud" ]; then
  NAMES="$(rclone lsf "$REMOTE" "${BK_INCLUDE[@]}" --files-only "${RC_OPTS[@]}" | grep -E '^(lmc_[0-9]{8}_[0-9]{6}|lmc-data-.*)\.tar\.gz(\.enc)?$' | sort || true)"
  [ -n "$NAMES" ] || { LOG "ERRORE: nessun backup trovato su $REMOTE"; exit 1; }
  if [ "$WHICH" = "latest" ]; then PICK="$(echo "$NAMES" | tail -n 1)"; else PICK="$(echo "$NAMES" | grep -F "$WHICH" | tail -n 1 || true)"; fi
  [ -n "$PICK" ] || { LOG "ERRORE: nessun backup con data «$WHICH». Elenco: restore.sh --cloud-list"; exit 1; }
  STAMP_R="$(echo "$PICK" | sed -E 's/^lmc-data-//; s/^lmc_//; s/\.tar\.gz(\.enc)?$//')"
  LOG "scarico dal cloud il backup $STAMP_R …"
  mkdir -p "$TMP/dl"
  rclone copy "$REMOTE" "$TMP/dl" --include "lmc-data-$STAMP_R.*" --include "lmc-secrets-$STAMP_R.*" --include "lmc_$STAMP_R.*" --include "lmc_secrets_$STAMP_R.*" --checksum "${RC_OPTS[@]}"
  DATA_ARCHIVE="$(ls "$TMP"/dl/lmc-data-* "$TMP"/dl/lmc_2* 2>/dev/null | head -n 1 || true)"
  SEC_ARCHIVE=""; [ "$WITH_ENV" = "1" ] && SEC_ARCHIVE="$(ls "$TMP"/dl/lmc-secrets-* "$TMP"/dl/lmc_secrets_* 2>/dev/null | head -n 1 || true)"
  LOG "scaricato e controllato: $(basename "$DATA_ARCHIVE") ($(du -h "$DATA_ARCHIVE" | cut -f1))"
else
  DATA_ARCHIVE="${POS[0]:-}"; SEC_ARCHIVE="${POS[1]:-}"
  [ -f "$DATA_ARCHIVE" ] || { echo "Uso: $0 <lmc-data-....tar.gz[.enc]> [lmc-secrets-....enc]   oppure   $0 --from-cloud latest   (vedi --help)"; exit 1; }
fi

case "$DATA_ARCHIVE" in *.enc) need_pass || { LOG "ERRORE: l'archivio è cifrato ma manca la password ($PASS_FILE)"; exit 1; } ;; esac

echo "ATTENZIONE: sostituirò database e foto con quelli del backup:"
echo "  $(basename "$DATA_ARCHIVE")"
[ -n "$SEC_ARCHIVE" ] && echo "  e .env/secret.key da $(basename "$SEC_ARCHIVE")"
if [ "${LMC_YES:-}" != "1" ]; then read -r -p "Scrivi SI per continuare: " A; [ "$A" = "SI" ] || { echo "Annullato."; exit 1; }; fi

# 1) estrae in una cartella temporanea e controlla PRIMA di toccare il sito
mkdir -p "$TMP/x"
EXTRACT_OK=1
case "$DATA_ARCHIVE" in
  *.enc) dec_stream < "$DATA_ARCHIVE" | tar -xzf - -C "$TMP/x" || EXTRACT_OK=0 ;;
  *)     tar -xzf "$DATA_ARCHIVE" -C "$TMP/x" || EXTRACT_OK=0 ;;
esac
[ "$EXTRACT_OK" = "1" ] || { LOG "ERRORE: impossibile aprire l'archivio (password di cifratura sbagliata o file danneggiato): non ho toccato nulla."; exit 1; }
[ -f "$TMP/x/lmc.db" ] || { LOG "ERRORE: l'archivio non contiene lmc.db (password sbagliata o file danneggiato): non ho toccato nulla."; exit 1; }
CHECK="$(python3 - "$TMP/x/lmc.db" <<'PY'
import sqlite3, sys
print(sqlite3.connect(sys.argv[1]).execute("PRAGMA integrity_check").fetchone()[0])
PY
)"
[ "$CHECK" = "ok" ] || { LOG "ERRORE: il database del backup non è integro ($CHECK): non ho toccato nulla."; exit 1; }
if [ -n "$SEC_ARCHIVE" ]; then
  mkdir -p "$TMP/s"
  dec_stream < "$SEC_ARCHIVE" | tar -xzf - -C "$TMP/s" || { LOG "ERRORE: impossibile decifrare i segreti (password diversa?)"; exit 1; }
fi

# 2) ferma il sito, conserva lo stato attuale, sostituisce
STAMP="$(date +%Y%m%d_%H%M%S)"
systemctl stop "$SERVICE" 2>/dev/null || true
[ -d "$APP_DIR/data" ] && mv "$APP_DIR/data" "$APP_DIR/data.prima-del-ripristino-$STAMP"
[ -d "$APP_DIR/foto" ] && mv "$APP_DIR/foto" "$APP_DIR/foto.prima-del-ripristino-$STAMP"
mkdir -p "$APP_DIR/data"
mv "$TMP/x/lmc.db" "$APP_DIR/data/lmc.db"
[ -d "$TMP/x/uploads" ] && mv "$TMP/x/uploads" "$APP_DIR/data/uploads"
if [ -d "$TMP/x/foto" ]; then mv "$TMP/x/foto" "$APP_DIR/foto"; else mkdir -p "$APP_DIR/foto"; fi
if [ -n "$SEC_ARCHIVE" ]; then
  [ -f "$TMP/s/.env" ] && cp -a "$TMP/s/.env" "$APP_DIR/.env"
  [ -f "$TMP/s/secret.key" ] && cp -a "$TMP/s/secret.key" "$APP_DIR/data/secret.key"
fi
chmod 600 "$APP_DIR/.env" "$APP_DIR/data/lmc.db" "$APP_DIR/data/secret.key" 2>/dev/null || true
chown -R "$APP_USER:$APP_USER" "$APP_DIR/data" "$APP_DIR/foto" "$APP_DIR/.env" 2>/dev/null || true
systemctl start "$SERVICE" 2>/dev/null || true
echo "Ripristino completato. Stato precedente conservato in $APP_DIR/data.prima-del-ripristino-$STAMP"
echo "Controlla: curl -s http://127.0.0.1:8010/health   e   journalctl -u $SERVICE -n 30"
