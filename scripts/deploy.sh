#!/bin/sh
set -e
cd "$(dirname "$0")/.."

# cleanup
rm -f .DS_Store
rm -f -- ./*/.DS_Store

# spelling
sh scripts/run_spelling.sh

# ruff
uv run ruff format
uv run ruff check

python scripts/gen_requirements.py

echo copying
rsync -uz requirements.txt entorb@entorb.net:nice-todo/
rsync -ruzv --no-links --delete --delete-excluded --exclude __pycache__ src/ entorb@entorb.net:nice-todo/src/

# echo installing packages
ssh entorb@entorb.net "pip3.11 install --user -r nice-todo/requirements.txt > /dev/null"

echo restarting nice-todo
ssh entorb@entorb.net "supervisorctl restart nice-todo"

echo DONE

# cspell:ignore: ruzv uz
