#!/bin/sh

# ensure we are in the root dir
cd $(dirname $0)/..

scp entorb@entorb.net:nice-todo/sqlite.db ./
