#!/usr/bin/env bash
# =====================================================================================================
# FASE 4 — Controllo del sito DOPO l'installazione.
# Uso:  bash verifica-online.sh https://dominio.it        (oppure http://IP se ancora senza dominio)
#       bash verifica-online.sh http://127.0.0.1:8010 --no-system     (solo controlli HTTP, per prove senza systemd)
# =====================================================================================================
BASE="${1:-}"; [ -n "$BASE" ] || { echo "Uso: $0 https://DOMINIO"; exit 1; }; BASE="${BASE%/}"
NOSYS=0; [ "${2:-}" = "--no-system" ] && NOSYS=1
BAD=0; WARN=0
ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠️  $*"; WARN=$((WARN+1)); }
bad()  { echo "  ❌ $*"; BAD=$((BAD+1)); }
code() { curl -s -o /dev/null -m 15 -w "%{http_code}" "$@" 2>/dev/null; }
APP="${APP_DIR:-/srv/lmc}"

if [ "$NOSYS" = "0" ]; then
echo "== Servizi"
for S in lmc nginx cron; do systemctl is-active --quiet $S && ok "$S attivo" || bad "$S NON attivo → systemctl status $S"; done
echo "== File di configurazione e permessi"
if [ -f "$APP/.env" ]; then
  [ "$(stat -c %a "$APP/.env")" = "600" ] && ok ".env con permessi 600" || bad ".env con permessi $(stat -c %a "$APP/.env") → chmod 600 $APP/.env"
  grep -q '^APP_MODE=production' "$APP/.env" && ok "APP_MODE=production" || bad "APP_MODE non è production nel .env"
  grep -q '^ADMIN_PASSWORD=.\+' "$APP/.env" && bad "ADMIN_PASSWORD è ancora nel .env: cancella la riga" || ok "nessuna ADMIN_PASSWORD nel .env"
  case "$BASE" in https://*) grep -q '^COOKIE_SECURE=1' "$APP/.env" && ok "COOKIE_SECURE=1" || bad "COOKIE_SECURE=1 mancante (sito in HTTPS)";; esac
  grep -q '^TRUST_PROXY=1' "$APP/.env" && ok "TRUST_PROXY=1" || bad "TRUST_PROXY=1 mancante"
  grep -q '^SMTP_HOST=.\+' "$APP/.env" && ok "SMTP configurato (email di conferma attive)" || warn "SMTP non configurato: le email delle prenotazioni finiscono in data/outbox.log"
else bad "$APP/.env non trovato"; fi
[ -f "$APP/deploy/lmc-backup.conf" ] && ok "deploy/lmc-backup.conf presente" || warn "deploy/lmc-backup.conf mancante"
fi

echo "== Sito $BASE"
H="$(curl -s -m 15 "$BASE/health")"; HC="$(code "$BASE/health")"
[ "$HC" = "200" ] && ok "/health risponde 200" || bad "/health risponde $HC"
echo "$H" | tr -d ' ' | grep -q '"mode":"production"' && ok "modalità production ($H)" || bad "modalità NON production: $H"
HOME_HTML="$(curl -s -m 20 "$BASE/")"; HOMEC="$(code "$BASE/")"
[ "$HOMEC" = "200" ] && ok "home 200" || bad "home risponde $HOMEC"
echo "$HOME_HTML" | grep -q 'demo-tag' && bad "compaiono bollini DEMO nella home" || ok "nessun bollino DEMO"
echo "$HOME_HTML" | grep -q '\[Segnaposto\]' && warn "ci sono ancora le foto segnaposto «[Segnaposto]»: carica le foto reali (Admin › Foto)" || ok "nessuna foto segnaposto"
echo "$HOME_HTML" | grep -q 'DA INSERIRE\|DA COMPLETARE' && bad "nella home compare un segnaposto [DA …]" || ok "nessun segnaposto [DA …]"
AC="$(code "$BASE/admin/")"; case "$AC" in 200|302) ok "/admin raggiungibile ($AC)";; *) bad "/admin risponde $AC";; esac
[ "$(code "$BASE/privacy")" = "200" ] && ok "/privacy 200" || bad "/privacy non risponde 200"
[ "$(code "$BASE/robots.txt")" = "200" ] && ok "robots.txt" || warn "robots.txt non risponde"
[ "$(code "$BASE/sitemap.xml")" = "200" ] && ok "sitemap.xml" || warn "sitemap.xml non risponde"
[ "$(code "$BASE/static/css/site.css")" = "200" ] && ok "file statici serviti" || bad "css non raggiungibile"
curl -sI -m 15 -H 'Accept-Encoding: gzip' "$BASE/" | grep -qi '^content-encoding: gzip' && ok "compressione gzip attiva" || warn "gzip non attivo (dietro nginx dovrebbe esserlo)"
curl -sI -m 15 "$BASE/" | grep -qi '^x-content-type-options: nosniff' && ok "intestazioni di sicurezza presenti" || warn "intestazioni di sicurezza assenti"
case "$BASE" in
  https://*)
    HOSTN="${BASE#https://}"; HOSTN="${HOSTN%%/*}"
    RC="$(code "http://$HOSTN/")"; case "$RC" in 301|302|308) ok "http → https (redirect $RC)";; *) warn "la porta 80 risponde $RC invece di reindirizzare a https";; esac
    END="$(echo | openssl s_client -servername "$HOSTN" -connect "$HOSTN:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)"
    if [ -n "$END" ]; then D=$(( ( $(date -d "$END" +%s) - $(date +%s) ) / 86400 )); [ "$D" -gt 14 ] && ok "certificato HTTPS valido ancora $D giorni" || bad "certificato in scadenza fra $D giorni"; else bad "certificato HTTPS non leggibile"; fi;;
  http://*) warn "sito in HTTP: microfono, PWA e installazione come app richiedono HTTPS → collega il dominio (deploy/collega-dominio.sh)";;
esac

if [ "$NOSYS" = "0" ]; then
echo "== Log di avvio (ultime 200 righe del servizio)"
LOGS="$(journalctl -u lmc -n 200 --no-pager 2>/dev/null)"
echo "$LOGS" | grep -qiE 'traceback|error|exception' && { bad "errori nel log:"; echo "$LOGS" | grep -iE 'traceback|error|exception' | head -8 | sed 's/^/     /'; } || ok "nessun errore nel log"
echo "$LOGS" | grep -q 'ATTENZIONE' && { warn "avvisi di configurazione:"; echo "$LOGS" | grep 'ATTENZIONE' | sort -u | sed 's/^/     /'; } || ok "nessun avviso di configurazione"
echo "== Backup"
[ -f /etc/cron.d/lmc-backup ] && ok "cron del backup installato ($(grep -c backup /etc/cron.d/lmc-backup) righe)" || bad "/etc/cron.d/lmc-backup mancante"
[ -s /root/.lmc-backup-pass ] && ok "password di cifratura presente (SALVALA fuori dal VPS)" || bad "/root/.lmc-backup-pass mancante"
if [ -f /var/backups/lmc/LAST_OK ]; then ok "ultimo backup riuscito: $(grep '^time=' /var/backups/lmc/LAST_OK | cut -d= -f2) · cloud: $(grep '^cloud=' /var/backups/lmc/LAST_OK | cut -d= -f2)"; else warn "nessun backup riuscito ancora: sudo $APP/deploy/backup.sh"; fi
fi
echo
echo "RISULTATO: $BAD problemi · $WARN avvisi"
exit $((BAD>0))
