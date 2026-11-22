#!/bin/sh
# Доступ с телефона/другого ПК в той же LAN (токен обязателен)
cd "$(dirname "$0")" || exit 1
exec sh ./run.sh serve --host 0.0.0.0 --open "$@"
