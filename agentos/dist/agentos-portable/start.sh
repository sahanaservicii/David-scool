#!/bin/sh
# Двойной клик/запуск: браузерный интерфейс на 127.0.0.1
cd "$(dirname "$0")" || exit 1
exec sh ./run.sh serve --open "$@"
