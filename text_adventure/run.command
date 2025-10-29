#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
python "$DIR/main.py" "$@"
