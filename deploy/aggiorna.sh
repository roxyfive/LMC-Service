#!/usr/bin/env bash
# =====================================================================================================
# Aggiorna il sito già online: backup di sicurezza → git pull → dipendenze → permessi su foto/ → riavvio → controllo /health.
# Le foto e i video nuovi (cartella foto/organizzate/) vengono pubblicati da soli all'avvio; quelli spostati o
# cancellati su git spariscono dal sito. Uso (come root sulla VPS):   bash /srv/lmc/deploy/aggiorna.sh
# =====================================================================================================
set -u
APP="${APP:-/srv/lmc}"; SVC_USER="${SVC_USER:-lmc}"
[ "$(id -u)" = "0" ] || { echo "Esegui come root: sudo bash $0"; exit 1; }
cd "$APP" || { echo "❌ $APP non esiste"; exit 1; }
echo "== 1/5 backup di sicurezza"
bash "$APP/deploy/backup.sh" >/dev/null 2>&1 && echo "  ✅ backup fatto" || echo "  ⚠️  backup non riuscito (controlla: bash deploy/backup-status.sh) — continuo comunque"
echo "== 2/5 git pull"
git pull --ff-only || { echo "❌ git pull non riuscito (modifiche locali o conflitto): risolvi a mano, il sito è rimasto com'era"; exit 1; }
echo "== 3/5 dipendenze"
"$APP/.venv/bin/pip" install -q -r requirements.txt && echo "  ✅ dipendenze ok"
echo "== 4/5 permessi (git pull da root crea file di root: il sito deve poterli leggere)"
chown -R "$SVC_USER:$SVC_USER" "$APP/foto" "$APP/data" 2>/dev/null; echo "  ✅ foto/ e data/ di $SVC_USER"
echo "== 5/5 riavvio + controllo"
systemctl restart lmc
for i in $(seq 1 30); do
  H="$(curl -s -m 3 http://127.0.0.1:8010/health || true)"
  case "$H" in *'"status":"ok"'*) echo "  ✅ sito attivo: $H"; break;; esac; sleep 1
  [ "$i" = 30 ] && { echo "❌ il sito non risponde: journalctl -u lmc -n 50"; exit 1; }
done
echo "Fatto. Foto/video nuovi pubblicati automaticamente (Admin › Foto per controllare)."
