#!/bin/sh

# ensure we are in the root dir
cd $(dirname $0)/..

uv run python -m src.delete_board "$1"
