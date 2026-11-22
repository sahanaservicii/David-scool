#!/usr/bin/env python3
"""Entry point: CLI by default, --web for server."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser(description="Свободный Голос - голосовой помощник")
    p.add_argument('--web', action='store_true', help='Запустить веб-интерфейс')
    p.add_argument('--host', default=None, help='Хост сервера (по умолчанию из config)')
    p.add_argument('--port', type=int, default=None, help='Порт сервера')
    p.add_argument('--config', help='Путь к config.json')
    p.add_argument('--status', action='store_true', help='Показать статус и выйти')
    p.add_argument('text', nargs='*', help='Текстовый запрос (CLI режим)')
    args, rest = p.parse_known_args()

    if args.web:
        from assistant.core.config import load_config
        from assistant.web.server import run_server
        cfg = load_config(args.config)
        host = args.host or cfg.get('server', {}).get('host', '127.0.0.1')
        port = args.port or cfg.get('server', {}).get('port', 8765)
        run_server(host=host, port=port, config_path=args.config)
        return 0

    # CLI mode
    from assistant.cli import main as cli_main
    argv = []
    if args.config:
        argv += ['--config', args.config]
    if args.status:
        argv += ['--status']
    if args.text:
        argv += args.text
    argv += rest
    return cli_main(argv)


if __name__ == '__main__':
    raise SystemExit(main())
