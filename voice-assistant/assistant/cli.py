from __future__ import annotations
import argparse
import json
import sys

from .core.engine import AssistantEngine


def main(argv=None):
    p = argparse.ArgumentParser(description="Свободный Голос - CLI")
    p.add_argument('text', nargs='*', help='Запрос (если пусто - интерактивный режим)')
    p.add_argument('--config', help='Путь к config.json')
    p.add_argument('--json', action='store_true', help='Вывод в JSON')
    p.add_argument('--status', action='store_true', help='Показать статус')
    p.add_argument('--session', default='cli', help='ID сессии')
    args = p.parse_args(argv)

    engine = AssistantEngine(args.config)
    if args.status:
        print(json.dumps(engine.status(), ensure_ascii=False, indent=2))
        return 0

    if args.text:
        q = ' '.join(args.text)
        res = engine.process(q, session_id=args.session)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(res['text'])
        return 0

    print(f"{engine.cfg.get('app',{}).get('name','Assistant')} (CLI). /help, /status, /exit")
    while True:
        try:
            line = input('> ')
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line in ('/exit', '/quit'):
            break
        if line == '/status':
            print(json.dumps(engine.status(), ensure_ascii=False, indent=2))
            continue
        if line == '/help':
            line = 'помощь'
        res = engine.process(line, session_id=args.session)
        print(res['text'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
