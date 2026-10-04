#!/bin/sh
set -e
cd "$(dirname "$0")/.."

echo "id  key"
echo "--  ---"

sqlite3 sqlite.db "SELECT id, key FROM board ORDER BY id;"
