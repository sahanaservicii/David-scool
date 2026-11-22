"""CLI: ask/run/list/show/selftest/doctor/serve/mem/route."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import replace
import os
from pathlib import Path

from .core import (CONFIG_PATH, DATA, EXPECTED_AGENTS, HOMELAB_DIR,
                   REGISTRY, ROOT, VERSION,
                   Context, Memory, answer, load_agents, load_config,
                   make_context, run_agent)
from .llm import describe, LLMClient
from .utils import table, truncate

ROUTES = [
    ("проверь пинг 192.168.1.1", "net.ping"),
    ("сканируй порты 192.168.1.1", "net.ports"),
    ("покажи arp таблицу", "net.arp"),
    ("кто в сети по mac", "net.arp"),
    ("какие у меня интерфейсы и шлюз", "net.iface"),
    ("разреши имя 192.168.1.1", "net.dns"),
    ("проверь доступность роутера http", "net.httpping"),
    ("разбей подсеть 192.168.1.0/24 на /26", "net.split"),
    ("сделай бэкап роутера", "hl.backup"),
    ("отправь уведомление на телефон", "hl.notify"),
    ("покажи инвентарь устройств", "net.inventory"),
    ("какой последний скан", "hl.state"),
    ("сравни инвентарь со сканом", "hl.diff"),
    ("проверь права файлов", "sec.perms"),
    ("сгенерируй пароль 24", "sec.genpass"),
    ("аудит камер видеонаблюдения", "sec.cameras"),
    ("проверь защитные заголовки веба", "sec.headers"),
    ("посчитай 2+2*10", "math.calc"),
    ("переведи 10 гигабайт в мегабайты", "math.unit"),
    ("сколько дней между датами 2026-11-15 2026-12-31", "math.date"),
    ("объясни cron */15 3 * * 1-5", "math.cron"),
    ("сократи текст до главного", "txt.summary"),
    ("сколько слов в тексте", "txt.stats"),
    ("сделай slug из заголовка", "txt.slug"),
    ("сравни два текста", "txt.diff"),
    ("конвертируй csv в json", "txt.csv2json"),
    ("добавь задачу купить диск", "todo.add"),
    ("покажи список задач", "todo.list"),
    ("план дня", "plan.day"),
    ("составь план обслуживания", "hl.plan"),
    ("запиши заметку про vlan", "note.add"),
    ("что такое wireguard", "doc.glossary"),
    ("сгенерируй каталог агентов", "doc.catalog"),
    ("покажи журнал прогонов", "doc.runs"),
    ("найди большие файлы", "fs.large"),
    ("посмотри хвост лога", "fs.tail"),
    ("определи тип файла", "fs.type"),
    ("версия windows", "win.info"),
    ("выполни cmd команду ipconfig", "win.cmd"),
    ("запусти powershell команду Get-Service", "win.ps"),
    ("сеть windows netstat", "win.net"),
    ("свободное место на дисках windows", "win.disk"),
    ("покажи службы windows", "win.services"),
    ("процессы windows", "win.process"),
    ("журнал событий windows ошибки", "win.eventlog"),
    ("локальные пользователи windows", "win.users"),
    ("планировщик задач windows", "win.tasks"),
    ("правила брандмауэра windows", "win.firewall"),
    ("обновления windows", "win.updates"),
    ("что умеешь windows", "win.help"),
]


def _ctx(args, dry_run=None):
    cfg = load_config()
    if dry_run is None:
        dry_run = not getattr(args, "live", False)
    ctx = make_context(cfg, dry_run=dry_run)
    ctx.llm_client = LLMClient(cfg)
    return ctx


def _print(res: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if res.get("ok"):
        head = res.get("name")
        if res.get("score") is not None and res.get("agent"):
            head = f"{res['agent']} · {res.get('name', '')}"
        print(f"— {head} ({res.get('ms', 0)} мс)")
        out = res.get("output")
        print(out if isinstance(out, str) else json.dumps(out, ensure_ascii=False,
                                                          indent=2, default=str))
    else:
        print(f"!! {res.get('error')}")
    alts = res.get("alternatives") or res.get("suggestions") or []
    if alts and not res.get("ok"):
        print("\nпохожие:")
        for a in alts[:5]:
            print(f"  {a['id']:<22} {a.get('name', '')}  (score {a['score']})")
    return 0 if res.get("ok") else 1


def cmd_ask(args) -> int:
    load_agents()
    ctx = _ctx(args)
    items = [x for x in args.text if x is not None]
    query = " ".join(items) if items else ""
    if args.agent and not query:
        query = ""
    res = answer(ctx, query, agent_id=args.agent, min_score=args.min_score)
    return _print(res, args.json)


def cmd_run(args) -> int:
    load_agents()
    agent = REGISTRY.get(args.agent_id)
    if not agent:
        print(f"нет агента {args.agent_id!r}. Список: agentos list", file=sys.stderr)
        return 2
    ctx = _ctx(args)
    res = run_agent(agent, ctx, " ".join(args.text or [""]))
    return _print({"ok": res.ok, "agent": agent.id, "name": agent.name,
                   "ms": res.ms, "output": res.output, "error": res.error}, args.json)


def cmd_list(args) -> int:
    load_agents()
    cats = REGISTRY.categories()
    if args.json:
        print(json.dumps([a.row() for a in REGISTRY.all()], ensure_ascii=False, indent=2))
        return 0
    total = 0
    for cat in sorted(cats):
        if args.category and cat != args.category:
            continue
        print(f"\n{cat} ({len(cats[cat])})")
        for a in cats[cat]:
            print(f"  {a.id:<22} {a.name}")
        total += len(cats[cat])
    print(f"\nвсего: {total}")
    return 0


def cmd_show(args) -> int:
    load_agents()
    a = REGISTRY.get(args.agent_id)
    if not a:
        print("не найдено")
        return 2
    print(f"{a.id} · {a.name}\nкатегория: {a.category}\n{a.description}")
    if a.keywords:
        print("ключевые слова: " + ", ".join(a.keywords))
    if a.examples:
        print("пример: agentos run %s \"%s\"" % (a.id, a.examples[0]))
    if a.needs:
        print("требует: " + ", ".join(a.needs))
    return 0


def selftest(live: bool = False, verbose: bool = False) -> int:
    reg = load_agents()
    tmp = Path(tempfile.mkdtemp(prefix="agentos-selftest-"))
    data, out = tmp / "data", tmp / "out"
    data.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    ctx = Context(cfg=cfg, data=data, out=out, dry_run=not live,
                  memory=Memory(data / "mem.sqlite"), llm_client=LLMClient(cfg))

    rows, failures = [], []
    for a in reg.all():
        if "windows" in a.needs and os.name != "nt":
            rows.append([a.id, "skip", "-", "нужен Windows"])
            continue
        sample = a.examples[0] if a.examples else ""
        dry = ctx.dry_run or "slow" in a.tags or "write" in a.tags
        agent_ctx = replace(ctx, dry_run=dry)
        res = run_agent(a, agent_ctx, sample)
        text = res.text()
        ok = res.ok and bool(text.strip())
        rows.append([a.id, "ok" if ok else "FAIL", f"{res.ms} мс",
                     truncate(text.replace("\n", " "), 46)])
        if not ok:
            failures.append((a, res))

    print(table(rows, ["агент", "итог", "время", "ответ"], align_right={2}))
    cats = reg.categories()
    print(f"\nкатегорий: {len(cats)} · агентов: {len(reg)}")
    for cat in sorted(cats):
        print(f"  {cat:<12} {len(cats[cat])}")

    # проверка маршрутизации
    good = 0
    misses = []
    for query, expected in ROUTES:
        ranked = REGISTRY.route(query, 3)
        got = ranked[0][0].id if ranked else None
        if got == expected:
            good += 1
        else:
            misses.append((query, expected, got, ranked[0][1] if ranked else 0))
    acc = 100 * good / len(ROUTES)
    print(f"\nмаршрутизация: {good}/{len(ROUTES)} ({acc:.0f}%)")
    if verbose or acc < 90:
        for q, exp, got, sc in misses:
            print(f"  miss: «{truncate(q, 42)}» → {got} (ждали {exp}, score {sc})")

    if failures:
        print(f"\nсбои ({len(failures)}):")
        for a, res in failures[:12]:
            print(f"  {a.id}: {res.error or 'пустой ответ'}")
        if verbose:
            for a, res in failures[:3]:
                for n in res.notes:
                    print(n)

    ok_all = not failures and acc >= 90
    print("\nИТОГ: " + ("ВСЁ РАБОТАЕТ" if ok_all else "ЕСТЬ ПРОБЛЕМЫ"))
    return 0 if ok_all else 1


def cmd_selftest(args) -> int:
    return selftest(live=args.live, verbose=args.verbose)


def cmd_doctor(args) -> int:
    load_agents()
    cfg = load_config()
    llm = describe(cfg)
    checks = [
        ("python", sys.version.split()[0], "ok"),
        ("агентов", str(len(REGISTRY)),
         "ok" if len(REGISTRY) == EXPECTED_AGENTS else "!!"),
        ("homelab.py", "есть" if (HOMELAB_DIR / "homelab.py").exists() else "НЕТ",
         "ok" if (HOMELAB_DIR / "homelab.py").exists() else "!!"),
        ("конфиг", str(CONFIG_PATH) if CONFIG_PATH.exists() else "по умолчанию", "ok"),
        ("данные", str(DATA), "ok"),
        ("LLM", f"да ({llm['url']})" if llm["available"] else "нет (не критично)", "ok"),
        ("сеть", cfg.get("network", "?"), "ok"),
        ("dry-run по умолчанию", str(cfg["safety"]["dry_run_default"]), "ok"),
    ]
    print(table([[a, b, c] for a, b, c in checks], ["что", "значение", ""]))
    st = Memory(DATA / "memory.sqlite").stats() if DATA.exists() else {}
    if st:
        print(f"\nпрогонов: {st['runs']}, успешных: {st['ok']}, "
              f"среднее: {st['avg_ms']} мс")
    print("\nпроверка агентов: agentos selftest")
    return 0


def cmd_mem(args) -> int:
    mem = Memory(DATA / "memory.sqlite")
    if args.what == "facts":
        for f in mem.facts(args.query or ""):
            print(f"{f['ts'][:16]}  {f['key']} = {truncate(f['value'], 70)}")
    elif args.what == "notes":
        for n in mem.notes(args.query or ""):
            print(f"#{n['id']} {n['ts'][:16]} [{n['tags']}] {truncate(n['text'], 80)}")
    elif args.what == "todos":
        for t in mem.todo_list(include_done=True):
            mark = "x" if t["done"] else " "
            print(f"[{mark}] #{t['id']} {t['text']} {t['due'] or ''}")
    else:
        for r in mem.runs(limit=args.limit, agent=args.query or None):
            print(f"{r['id']:>4} {r['ts'][11:19]} {r['agent']:<20} "
                  f"{'ok' if r['ok'] else 'ERR':<3} {r['ms']:>5} мс  "
                  f"{truncate(r['query'], 40)}")
    return 0


def cmd_route(args) -> int:
    load_agents()
    q = " ".join(args.text)
    ranked = REGISTRY.route(q, 8)
    if not ranked:
        print("ничего не подошло")
        return 1
    for a, s in ranked:
        print(f"{s:>7.2f}  {a.id:<22} {a.name}")
    return 0


def cmd_serve(args) -> int:
    from .server import serve
    load_agents()
    return serve(_ctx(args), port=args.port, host=args.host,
                 open_browser=args.open)


def cmd_catalog(args) -> int:
    load_agents()
    from .agents.docs import catalog
    res = run_agent(REGISTRY.get("doc.catalog"), _ctx(args, dry_run=False), "")
    print(res.text())
    return 0 if res.ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agentos",
        description="Офлайн-мультиагентная система: 100 мини-агентов для дома и сети",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Примеры:\n"
            "  agentos \"проверь пинг 192.168.1.1\"\n"
            "  agentos run sec.cameras \"\" --live\n"
            "  agentos selftest -v\n"
            "  agentos list\n"
        ),
    )
    p.add_argument("--version", action="version", version=f"agentos {VERSION}")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("ask", help="запрос на естественном языке")
    a.add_argument("text", nargs="*")
    a.add_argument("--agent", help="принудительно выбрать агента")
    a.add_argument("--json", action="store_true")
    a.add_argument("--live", action="store_true", help="выполнять, а не dry-run")
    a.add_argument("--min-score", type=float, default=3.0)
    a.set_defaults(func=cmd_ask)

    r = sub.add_parser("run", help="запустить агента по id")
    r.add_argument("agent_id")
    r.add_argument("text", nargs="*")
    r.add_argument("--json", action="store_true")
    r.add_argument("--live", action="store_true")
    r.set_defaults(func=cmd_run)

    ls = sub.add_parser("list", help="список агентов")
    ls.add_argument("--category")
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list)

    sh = sub.add_parser("show", help="подробности об агенте")
    sh.add_argument("agent_id")
    sh.set_defaults(func=cmd_show)

    st = sub.add_parser("selftest", help="проверить все агенты и маршрутизацию")
    st.add_argument("--live", action="store_true", help="разрешить реальные операции")
    st.add_argument("-v", "--verbose", action="store_true")
    st.set_defaults(func=cmd_selftest)

    d = sub.add_parser("doctor", help="состояние системы")
    d.set_defaults(func=cmd_doctor)

    m = sub.add_parser("mem", help="память: runs/facts/notes/todos")
    m.add_argument("what", nargs="?", default="runs",
                   choices=["runs", "facts", "notes", "todos"])
    m.add_argument("query", nargs="?")
    m.add_argument("--limit", type=int, default=20)
    m.set_defaults(func=cmd_mem)

    rt = sub.add_parser("route", help="показать, как маршрутизируется запрос")
    rt.add_argument("text", nargs="+")
    rt.set_defaults(func=cmd_route)

    sv = sub.add_parser("serve", help="локальный HTTP API (127.0.0.1)")
    sv.add_argument("--port", type=int, default=8765)
    sv.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 (по умолчанию) или 0.0.0.0 для доступа из LAN")
    sv.add_argument("--open", action="store_true",
                    help="открыть браузер после запуска")
    sv.add_argument("--live", action="store_true",
                    help="разрешить изменяющие действия через API")
    sv.set_defaults(func=cmd_serve)

    c = sub.add_parser("catalog", help="пересобрать CATALOG.md")
    c.set_defaults(func=cmd_catalog)
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    known = {"ask", "run", "list", "show", "selftest", "doctor", "mem",
             "route", "serve", "catalog"}
    if argv and argv[0] not in known and not argv[0].startswith("-"):
        argv = ["ask"] + argv
    elif not argv:
        argv = ["doctor"]
    args = build_parser().parse_args(argv)
    if not getattr(args, "func", None):
        build_parser().print_help()
        return 0
    try:
        return args.func(args)
    except BrokenPipeError:          # вывод в head/less — это норма, не ошибка
        try:
            sys.stdout.close()
        except OSError:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
