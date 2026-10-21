#!/usr/bin/env bash
# =====================================================================================================
# Stato dei backup LMC Service.
#   backup-status.sh                    riepilogo: ultimo backup riuscito, età, file locali e sul cloud IONOS
#   backup-status.sh --check            esce con 1 se l'ultimo backup riuscito è più vecchio di MAX_AGE_HOURS (26)
#   backup-status.sh --check --alert    come sopra e in più manda l'avviso (email + WhatsApp) — è ciò che fa il cron delle 08:00
#   backup-status.sh --verify-remote    controlla ora che i backup più recenti sul cloud siano integri (dimensione + impronta)
# =====================================================================================================
set -Eeuo pipefail
# shellcheck disable=SC1091
. "$(dirname "$(readlink -f "$0")")/lib-backup.sh"
CHECK=0; ALERT=0; VERIFY=0
for a in "$@"; do case "$a" in --check) CHECK=1 ;; --alert) ALERT=1 ;; --verify-remote) VERIFY=1 ;; -h|--help) sed -n '2,9p' "$0"; exit 0 ;; esac; done

AGE_H=-1; LASTTXT="mai"
if [ -f "$BACKUP_DIR/LAST_OK" ]; then
  T="$(grep '^time=' "$BACKUP_DIR/LAST_OK" | cut -d= -f2-)"
  EPOCH="$(date -d "$T" +%s 2>/dev/null || echo 0)"
  AGE_H=$(( ( $(date +%s) - EPOCH ) / 3600 ))
  LASTTXT="$T ($AGE_H ore fa) — cloud: $(grep '^cloud=' "$BACKUP_DIR/LAST_OK" | cut -d= -f2-)"
fi

if [ "$VERIFY" = "1" ]; then
  cloud_setup || { LOG "copia cloud non configurata"; exit 1; }
  RES=0
  for f in $(ls -1t "$BACKUP_DIR"/lmc_2* "$BACKUP_DIR"/lmc_secrets_* "$BACKUP_DIR"/lmc-data-* "$BACKUP_DIR"/lmc-secrets-* 2>/dev/null | head -n 2); do verify_remote_file "$f" || RES=1; done
  [ "$RES" = "0" ] || { [ "$ALERT" = "1" ] && send_alert "Backup su IONOS non integro" "Il controllo manuale ha trovato file mancanti o diversi sul cloud IONOS."; exit 1; }
  exit 0
fi

if [ "$CHECK" = "1" ]; then
  if [ "$AGE_H" -lt 0 ] || [ "$AGE_H" -ge "$MAX_AGE_HOURS" ]; then
    LOG "PROBLEMA: nessun backup riuscito nelle ultime $MAX_AGE_HOURS ore (ultimo: $LASTTXT)"
    [ "$ALERT" = "1" ] && send_alert "Backup notturno MANCANTE" "Nessun backup riuscito nelle ultime $MAX_AGE_HOURS ore (ultimo: $LASTTXT). Controlla: tail -n 50 /var/log/lmc-backup.log"
    exit 1
  fi
  LOG "ok: ultimo backup riuscito $LASTTXT"
  exit 0
fi

echo "== Backup LMC Service =="
echo "Configurazione : ${CONF_USED:-nessun file (valori predefiniti)}"
echo "Cartella locale: $BACKUP_DIR   (rotazione: $KEEP_DAYS giorni)"
echo "Ultimo riuscito: $LASTTXT"
echo "File locali:"
ls -lh "$BACKUP_DIR" 2>/dev/null | awk '/lmc[-_]/{printf "  %8s  %s %s %s  %s\n",$5,$6,$7,$8,$9}' || true
if cloud_setup; then
  echo "Copia cloud     : $REMOTE   (rotazione: $REMOTE_KEEP_DAYS giorni)"
  rclone lsl "$REMOTE" "${BK_INCLUDE[@]}" "${RC_OPTS[@]}" 2>&1 | sort -k4 | awk '{printf "  %8.1fM  %s %s  %s\n",$1/1048576,$2,substr($3,1,8),$4}' || echo "  (non raggiungibile)"
else
  echo "Copia cloud     : non configurata"
fi
