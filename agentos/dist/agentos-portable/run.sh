#!/bin/sh
# Переносимый запуск: нужен только python3 (3.10+).
cd "$(dirname "$0")" || exit 1
command -v python3 >/dev/null 2>&1 || { echo "нужен python3 3.10+"; exit 1; }
exec python3 -m agentos "$@"
