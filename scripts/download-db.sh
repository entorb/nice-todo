#!/bin/sh

# ensure we are in the root dir
cd "$(dirname "$0")/.."

# consistent snapshot via sqlite backup()
# plain scp of a live WAL-mode DB would copy the main file only, missing sqlite.db-wal and risking corruption
ssh entorb@entorb.net "cd nice-todo && python3.11 -c \"import sqlite3; s=sqlite3.connect('sqlite.db'); d=sqlite3.connect('sqlite-snapshot.db'); s.backup(d); d.close(); s.close()\""
scp entorb@entorb.net:nice-todo/sqlite-snapshot.db ./sqlite.db
ssh entorb@entorb.net "rm -f nice-todo/sqlite-snapshot.db"
