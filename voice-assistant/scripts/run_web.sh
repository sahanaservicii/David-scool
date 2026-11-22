#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
HOST="${ASSISTANT_HOST:-127.0.0.1}"
PORT="${ASSISTANT_PORT:-8765}"
exec python3 main.py --web --host "$HOST" --port "$PORT" "$@"
