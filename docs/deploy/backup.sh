#!/usr/bin/env bash
# Backup giornaliero: database SQLite (copia consistente) + cartella foto/video.
set -euo pipefail
APP=/srv/lmc
DEST=/var/backups/lmc
STAMP=$(date +%F)
mkdir -p "$DEST"
TMP=$(mktemp -d)
sqlite3 "$APP/data/lmc.db" ".backup '$TMP/lmc.db'"
cp -r "$APP/data/uploads" "$TMP/uploads"
tar -czf "$DEST/lmc-$STAMP.tar.gz" -C "$TMP" .
rm -rf "$TMP"
find "$DEST" -name 'lmc-*.tar.gz' -mtime +14 -delete
echo "$(date -Is) backup ok: lmc-$STAMP.tar.gz"
