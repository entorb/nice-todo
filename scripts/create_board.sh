#!/bin/sh

# ensure we are in the root dir
cd "$(dirname "$0")/.." || exit 1

uv run python -m src.create_board "$1"
