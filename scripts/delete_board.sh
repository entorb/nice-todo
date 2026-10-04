#!/bin/sh
set -e
cd "$(dirname "$0")/.."

uv run python -m src.delete_board "$1"
