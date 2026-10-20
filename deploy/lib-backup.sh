#!/usr/bin/env bash
# =====================================================================================================
# Funzioni condivise da backup.sh, restore.sh e backup-status.sh (non si lancia da solo).
# Configurazione: prima trovata tra  $LMC_BACKUP_CONF  ·  deploy/lmc-backup.conf  ·  /etc/lmc-backup.conf
# (modello: deploy/lmc-backup.conf.example). Le chiavi di IONOS stanno SOLO lì: il file è escluso da git.
# =====================================================================================================
LIB_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
umask 077

# le variabili già presenti nell'ambiente (es. VERIFY_DOWNLOAD=1 backup-status.sh ...) hanno la precedenza sul file di configurazione
_KEYS="APP_DIR BACKUP_DIR KEEP_DAYS REMOTE_KEEP_DAYS PASS_FILE ENCRYPT VERIFY_DOWNLOAD MAX_AGE_HOURS S3_ENDPOINT S3_ACCESS_KEY S3_SECRET_KEY S3_BUCKET S3_PREFIX S3_REGION RCLONE_REMOTE APP_USER"
declare -A _ENVSAVE=()
for _k in $_KEYS; do if [ -n "${!_k+x}" ]; then _ENVSAVE[$_k]="${!_k}"; fi; done
CONF_USED=""
for _c in "${LMC_BACKUP_CONF:-}" "$LIB_DIR/lmc-backup.conf" /etc/lmc-backup.conf; do
  if [ -n "$_c" ] && [ -f "$_c" ]; then
    # shellcheck disable=SC1090
    . "$_c"
    CONF_USED="$_c"
    break
  fi
done
for _k in "${!_ENVSAVE[@]}"; do printf -v "$_k" '%s' "${_ENVSAVE[$_k]}"; done
: "${APP_DIR:=$(dirname "$LIB_DIR")}"
: "${BACKUP_DIR:=/var/backups/lmc}"
: "${KEEP_DAYS:=7}"                  # rotazione locale
: "${REMOTE_KEEP_DAYS:=$KEEP_DAYS}"  # rotazione su IONOS
: "${PASS_FILE:=/root/.lmc-backup-pass}"
: "${ENCRYPT:=1}"                    # 1 = anche l'archivio dati è cifrato (consigliato: il database contiene le chiavi API)
: "${VERIFY_DOWNLOAD:=0}"            # 1 = verifica la copia cloud scaricandola e confrontandola byte per byte
: "${MAX_AGE_HOURS:=26}"
: "${S3_ENDPOINT:=}" ; : "${S3_ACCESS_KEY:=}" ; : "${S3_SECRET_KEY:=}" ; : "${S3_BUCKET:=}" ; : "${S3_PREFIX:=lmc}" ; : "${S3_REGION:=}"
: "${RCLONE_REMOTE:=}"               # alternativa: un remote già configurato a mano con "rclone config"
: "${APP_USER:=lmc}"

LOG() { echo "$(date -Is) $*"; }

# esegue un comando come utente del sito (lmc) se siamo root: così database e file non diventano di proprietà di root
as_app_user() {
  if [ "$(id -u)" = "0" ] && [ -z "${LMC_NO_RUNUSER:-}" ] && id "$APP_USER" >/dev/null 2>&1; then
    runuser -u "$APP_USER" -- "$@"
  else
    "$@"
  fi
}

conf_warn_permissions() {
  [ -n "$CONF_USED" ] || return 0
  local mode; mode="$(stat -c %a "$CONF_USED" 2>/dev/null || echo 600)"
  case "$mode" in *00) : ;; *) LOG "ATTENZIONE: $CONF_USED ha permessi $mode: contiene le chiavi di IONOS, esegui  chmod 600 $CONF_USED" ;; esac
}

# ---------- copia cloud (IONOS Object Storage = S3 compatibile) ----------
REMOTE=""
cloud_setup() {
  REMOTE=""
  if [ -n "$S3_BUCKET" ] && [ -n "$S3_ENDPOINT" ] && [ -n "$S3_ACCESS_KEY" ] && [ -n "$S3_SECRET_KEY" ]; then
    local ep="$S3_ENDPOINT"
    case "$ep" in http://*|https://*) : ;; *) ep="https://$ep" ;; esac
    # remote "lmcs3" definito solo tramite variabili d'ambiente: nessun file con le chiavi viene scritto altrove
    export RCLONE_CONFIG="${RCLONE_CONFIG:-/dev/null}"
    export RCLONE_CONFIG_LMCS3_TYPE=s3 RCLONE_CONFIG_LMCS3_PROVIDER=Other RCLONE_CONFIG_LMCS3_ENV_AUTH=false
    export RCLONE_CONFIG_LMCS3_ACCESS_KEY_ID="$S3_ACCESS_KEY" RCLONE_CONFIG_LMCS3_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
    export RCLONE_CONFIG_LMCS3_ENDPOINT="$ep" RCLONE_CONFIG_LMCS3_NO_CHECK_BUCKET=true
    [ -n "$S3_REGION" ] && export RCLONE_CONFIG_LMCS3_REGION="$S3_REGION"
    REMOTE="lmcs3:${S3_BUCKET}${S3_PREFIX:+/$S3_PREFIX}"
  elif [ -n "$RCLONE_REMOTE" ]; then
    REMOTE="$RCLONE_REMOTE"
  fi
  [ -n "$REMOTE" ]
}

RC_OPTS=(--retries 3 --low-level-retries 5 --timeout 120s --contimeout 20s --quiet)

remote_info() {      # nome file -> "dimensione md5" sul cloud ("-1 -" se non c'è; md5 "-" se il cloud non lo fornisce)
  rclone lsjson "$REMOTE" --files-only --hash --include "$1" "${RC_OPTS[@]}" 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = []
if not d:
    print("-1 -")
else:
    print(d[0]["Size"], (d[0].get("Hashes") or {}).get("md5", "-"))'
}

# Verifica che il file sia davvero arrivato e integro sul cloud:
#   1) presente e con la STESSA DIMENSIONE   2) impronta md5 identica; se il cloud non la fornisce, confronto BYTE PER BYTE (scarica e confronta)
#   (VERIFY_DOWNLOAD=1 forza sempre il confronto byte per byte)
verify_remote_file() {
  local f="$1" name ls rs rm lm mode err
  name="$(basename "$f")"
  ls="$(stat -c %s "$f")"
  read -r rs rm <<<"$(remote_info "$name")"
  if [ "$rs" != "$ls" ]; then
    if [ "$rs" = "-1" ]; then LOG "ERRORE verifica cloud: $name NON presente su $REMOTE"; else LOG "ERRORE verifica cloud: $name dimensione locale $ls byte diversa da quella sul cloud ($rs byte)"; fi
    return 1
  fi
  lm="$(md5sum "$f" | cut -d' ' -f1)"
  mode="md5"
  if [ "$rm" != "-" ] && [ "$rm" != "$lm" ]; then
    LOG "ERRORE verifica cloud: $name ha la dimensione giusta ma l'impronta md5 sul cloud è diversa"
    return 1
  fi
  if [ "$rm" = "-" ] || [ "$VERIFY_DOWNLOAD" = "1" ]; then
    mode="confronto byte per byte"
    err="$(mktemp)"
    if ! rclone check "$(dirname "$f")" "$REMOTE" --one-way --download --include "$name" "${RC_OPTS[@]}" 2>"$err"; then
      LOG "ERRORE verifica cloud: $name ha la dimensione giusta ma il contenuto non coincide ($(tr '\n' ' ' < "$err" | cut -c1-160))"
      rm -f "$err"
      return 1
    fi
    rm -f "$err"
  fi
  LOG "verifica cloud ok: $name ($ls byte, controllo: $mode)"
}

# ---------- cifratura ----------
need_pass() { [ -s "$PASS_FILE" ]; }
enc_stream() { openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass "file:$PASS_FILE"; }
dec_stream() { openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$PASS_FILE"; }

# avviso (email al titolare + WhatsApp a chi è di turno) tramite il sito stesso
send_alert() {
  local subject="$1" msg="$2"
  LOG "AVVISO: $subject – $msg"
  local cmd="${ALERT_CMD:-}"
  if [ -n "$cmd" ]; then
    # shellcheck disable=SC2086
    $cmd "$subject" "$msg" || true
  elif [ -x "$APP_DIR/.venv/bin/python" ] && [ -f "$LIB_DIR/backup-alert.py" ]; then
    as_app_user "$APP_DIR/.venv/bin/python" "$LIB_DIR/backup-alert.py" "$subject" "$msg" || LOG "(invio dell'avviso non riuscito: controlla SMTP/Twilio)"
  fi
}
