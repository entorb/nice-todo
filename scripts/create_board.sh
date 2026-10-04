#!/bin/sh
set -e
cd "$(dirname "$0")/.."

uv run python -m src.create_board "$1"
