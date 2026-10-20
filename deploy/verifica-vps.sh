#!/usr/bin/env bash
# =====================================================================================================
# FASE 1 — Controllo della VPS PRIMA dell'installazione (non modifica nulla).
# Uso (come root sulla VPS):   bash verifica-vps.sh [dominio.it]
# Incolla l'output completo a Claude: dirà cosa serve prima di installare.
# =====================================================================================================
DOM="${1:-}"
BAD=0; WARN=0
ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠️  $*"; WARN=$((WARN+1)); }
bad()  { echo "  ❌ $*"; BAD=$((BAD+1)); }
echo "== Sistema"
. /etc/os-release 2>/dev/null || true
echo "  $PRETTY_NAME · kernel $(uname -r) · $(uname -m) · uptime $(uptime -p 2>/dev/null)"
case "${VERSION_ID:-}" in 22.04|24.04) ok "Ubuntu supportato ($VERSION_ID)";; *) warn "Sistema ${PRETTY_NAME:-sconosciuto}: lo script è pensato per Ubuntu 22.04/24.04";; esac
[ "$(id -u)" = "0" ] && ok "sei root" || bad "non sei root: usa  sudo -i"
echo "== Risorse"
MEM=$(awk '/MemTotal/{printf "%d",$2/1024}' /proc/meminfo); CPU=$(nproc); DISK=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
echo "  RAM ${MEM} MB · CPU ${CPU} · disco libero ${DISK} GB"
[ "$MEM" -ge 900 ] && ok "RAM sufficiente" || warn "RAM bassa (<1 GB): il sito funziona ma con un solo worker; aggiungi uno swap"
[ "$DISK" -ge 10 ] && ok "disco sufficiente" || warn "poco spazio libero (<10 GB): foto/video e backup potrebbero riempirlo"
echo "== Rete"
IP="$(curl -4 -s -m 8 https://api.ipify.org 2>/dev/null || true)"
[ -n "$IP" ] && ok "IP pubblico della VPS: $IP" || warn "non riesco a ricavare l'IP pubblico (uscita internet bloccata?)"
curl -sI -m 8 https://archive.ubuntu.com >/dev/null 2>&1 && ok "uscita HTTPS verso i repository Ubuntu" || warn "nessuna uscita HTTPS: apt/pip/certbot non funzioneranno"
echo "== Porte in ascolto sulla VPS"
for P in 22 80 443; do
  L="$(ss -tlnpH "sport = :$P" 2>/dev/null | awk '{print $NF}' | head -1)"
  case "$P:$L" in
    22:*) [ -n "$L" ] && ok "porta 22 (SSH) in ascolto" || warn "SSH non risulta in ascolto sulla 22";;
    *:) ok "porta $P libera (la userà nginx)";;
    *) bad "porta $P già occupata da: $L  → va fermato/disinstallato (es. apache2, plesk) prima di installare nginx";;
  esac
done
for S in apache2 httpd plesk psa; do systemctl is-active --quiet $S 2>/dev/null && bad "servizio $S attivo: confligge con nginx"; done
echo "== Firewall sulla VPS (ufw/iptables)"
if command -v ufw >/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
  for P in 22 80 443; do ufw status | grep -qE "^$P(/tcp)? +ALLOW" && ok "ufw consente $P" || bad "ufw NON consente $P → ufw allow $P/tcp"; done
else ok "ufw non attivo (il firewall è quello del pannello IONOS)"; fi
iptables -S INPUT 2>/dev/null | grep -qE "^-P INPUT (DROP|REJECT)" && warn "iptables INPUT in DROP: verifica che 22/80/443 siano consentite" || true
echo "== DNS${DOM:+ di $DOM}"
if [ -n "$DOM" ]; then
  A="$(getent ahostsv4 "$DOM" 2>/dev/null | awk '{print $1}' | sort -u | tr '\n' ' ')"
  if [ -z "$A" ]; then bad "$DOM non risolve: crea il record A nel pannello domini IONOS (può servire da pochi minuti a qualche ora)"
  elif [ -n "$IP" ] && echo "$A" | grep -qw "$IP"; then ok "$DOM → $A (corrisponde all'IP della VPS)"
  else bad "$DOM → $A ma la VPS è $IP: correggi il record A (senza questo il certificato HTTPS non si può emettere)"; fi
else echo "  (nessun dominio indicato: puoi procedere con l'IP e collegare il dominio dopo)"; fi
echo
echo "DA CONTROLLARE DAL TUO PC (il firewall IONOS sta fuori dalla VPS e da qui non si vede):"
echo "  Windows PowerShell:  Test-NetConnection ${IP:-IP_VPS} -Port 80   e   -Port 443   e   -Port 22"
echo "  Mac/Linux:           nc -vz ${IP:-IP_VPS} 80   (e 443, 22)    — la 80/443 risponderanno solo dopo l'installazione di nginx"
echo "  Se 22/80/443 risultano chiuse: Cloud Panel IONOS › Server › la tua VPS › Rete › Criteri firewall → aggiungi regole IN per TCP 22, 80, 443."
echo
echo "RISULTATO: $BAD bloccanti · $WARN avvisi"
exit $((BAD>0))
