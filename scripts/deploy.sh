#!/bin/sh

# ensure we are in the root dir
cd $(dirname $0)/..

# exit upon error
set -e

# cleanup
rm -f .DS_Store
rm -f */.DS_Store

# ruff
uv run ruff format
uv run ruff check

python scripts/gen_requirements.py

echo copying
rsync -uz requirements.txt entorb@entorb.net:nicegui-todo/
rsync -ruzv --no-links --delete --delete-excluded --exclude __pycache__ src/ entorb@entorb.net:nicegui-todo/src/

# echo installing packages
ssh entorb@entorb.net "pip3.11 install --user -r nicegui-todo/requirements.txt > /dev/null"

echo restarting nicegui-todo
ssh entorb@entorb.net "supervisorctl restart nicegui-todo"

echo DONE

# cspell:ignore: ruzv uz
