#!/bin/sh

# ensure we are in the root dir
cd $(dirname $0)/..

echo "id  key"
echo "--  ---"

sqlite3 sqlite.db "SELECT id, key FROM board ORDER BY id;"
