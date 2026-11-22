"""Быт: задачи, заметки, план дня, привычки, таймер, решения."""
from __future__ import annotations

import re
from datetime import datetime, date, timedelta

from ..core import Context, agent
from ..utils import kv, parse_kv, table, truncate


def _mem(ctx: Context):
    if not ctx.memory:
        raise RuntimeError("память недоступна")
    return ctx.memory


@agent("todo.add", "Добавить задачу", "life",
       "Создаёт задачу со сроком (due=YYYY-MM-DD) в локальной базе",
       keywords=("задача", "todo", "напомни", "добавь дело", "срок"),
       examples=("due=2026-12-01 проверить бэкап роутера",), needs=())
def todo_add(ctx: Context, text: str):
    params, rest = parse_kv(text)
    title = rest.strip()
    if not title:
        raise ValueError("что сделать?")
    due = params.get("due", "")
    if due:
        date.fromisoformat(due)
    tid = _mem(ctx).todo_add(title, due)
    return f"#{tid} добавлено: {title}" + (f" (до {due})" if due else "")


@agent("todo.list", "Список задач", "life",
       "Показывает открытые задачи, просроченные помечены",
       keywords=("задачи", "todo list", "список дел", "что делать", "планы"),
       examples=("",), needs=())
def todo_list(ctx: Context, text: str):
    rows = _mem(ctx).todo_list(include_done="все" in text.lower())
    if not rows:
        return "открытых задач нет"
    today = date.today()
    out = []
    for r in rows:
        mark = "!"
        if r["due"]:
            try:
                d = date.fromisoformat(r["due"])
                mark = "ПРОСРОЧЕНО" if d < today else f"до {r['due']}"
            except ValueError:
                mark = r["due"]
        out.append([r["id"], r["text"], mark])
    return table(out, ["#", "задача", "срок"], align_right={0})


@agent("todo.done", "Закрыть задачу", "life",
       "Отмечает задачу выполненной по номеру",
       keywords=("выполнено", "закрой задачу", "done", "готово", "сделал"),
       examples=("1",), needs=())
def todo_done(ctx: Context, text: str):
    m = re.search(r"\d+", text)
    if not m:
        raise ValueError("укажи номер задачи")
    tid = int(m.group())
    if _mem(ctx).todo_done(tid):
        return f"задача #{tid} закрыта"
    return f"задача #{tid} не найдена или уже закрыта"


@agent("note.add", "Заметка", "life",
       "Сохраняет заметку с тегами (tags=сеть,идея)",
       keywords=("заметка", "note", "запиши мысль", "сохрани текст", "идея"),
       examples=("tags=сеть Проверить изоляцию камер в отдельном VLAN",), needs=())
def note_add(ctx: Context, text: str):
    params, rest = parse_kv(text)
    if not rest.strip():
        raise ValueError("текст заметки пуст")
    tags = params.get("tags", "")
    nid = _mem(ctx).note_add(rest.strip(), tags)
    return f"заметка #{nid} сохранена" + (f" [теги: {tags}]" if tags else "")


@agent("note.search", "Поиск заметок", "life",
       "Ищет сохранённые заметки по слову или тегу",
       keywords=("найди заметку", "поиск заметок", "что я писал", "заметки"),
       examples=("сеть",), needs=())
def note_search(ctx: Context, text: str):
    query = text.strip()
    rows = _mem(ctx).notes(like=query, limit=20)
    if not rows:
        return f"заметок по «{query}» нет" if query else "заметок нет"
    out = [[r["id"], r["ts"][:16], truncate(r["text"], 70), r["tags"]]
           for r in rows]
    return table(out, ["#", "когда", "заметка", "теги"], align_right={0})


@agent("plan.day", "План дня", "life",
       "Собирает план на день из задач и типовых блоков",
       keywords=("план дня", "распорядок", "schedule", "что сегодня", "день"),
       examples=("",), needs=())
def plan_day(ctx: Context, text: str):
    todos = _mem(ctx).todo_list()[:6]
    now = datetime.now()
    blocks = [
        ("09:00–10:00", "проверка сети и бэкапов: net.doctor, hl.state"),
        ("10:00–12:00", "глубокая работа без отвлечений"),
        ("12:00–13:00", "обед и прогулка"),
        ("13:00–16:00", "работа/задачи из списка"),
        ("16:00–16:30", "разбор журнала агентов и заметок"),
        ("18:00–19:00", "спорт"),
        ("21:00–21:30", "итоги дня, план на завтра"),
    ]
    lines = [f"План на {now:%d.%m.%Y}:", "", "Опорные блоки:"]
    lines += [f"  {a}  {b}" for a, b in blocks]
    if todos:
        lines += ["", "Задачи (по приоритету срока):"]
        for t in todos:
            due = f" — до {t['due']}" if t["due"] else ""
            lines.append(f"  □ #{t['id']} {t['text']}{due}")
    else:
        lines += ["", "Открытых задач нет — добавь: todo.add \"...\" due=2026-12-01"]
    return "\n".join(lines)


@agent("review.week", "Итоги недели", "life",
       "Сводка за неделю: прогоны агентов, задачи, привычки",
       keywords=("итоги недели", "review", "что сделано", "неделя", "ретро"),
       examples=("",), needs=())
def review_week(ctx: Context, text: str):
    mem = _mem(ctx)
    runs = mem.runs(limit=200)
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    week_runs = [r for r in runs if r["ts"] >= week_ago]
    by_agent: dict[str, int] = {}
    for r in week_runs:
        by_agent[r["agent"]] = by_agent.get(r["agent"], 0) + 1
    todos = mem.todo_list()
    done = mem.todo_list(include_done=True)
    done_week = [t for t in done if t["done_ts"] and t["done_ts"] >= week_ago]
    top = sorted(by_agent.items(), key=lambda x: -x[1])[:6]
    return "\n".join([
        f"Итоги за 7 дней (до {datetime.now():%d.%m.%Y}):",
        f"  запусков агентов: {len(week_runs)} "
        f"(успешных {sum(1 for r in week_runs if r['ok'])})",
        "  чаще всего: " + (", ".join(f"{a} ×{n}" for a, n in top) or "—"),
        f"  закрыто задач: {len(done_week)}",
        f"  открыто сейчас: {len(todos)}",
    ])


@agent("habit.log", "Отметка привычки", "life",
       "Отмечает привычку за сегодня и считает серию дней",
       keywords=("привычка", "habit", "серия", "каждый день", "streak"),
       examples=("habit=зарядка",), needs=())
def habit_log(ctx: Context, text: str):
    params, _ = parse_kv(text)
    name = (params.get("habit") or "привычка").strip()
    mem = _mem(ctx)
    today = date.today()
    mem.fact_set(f"habit:{name}:{today.isoformat()}", "1", tags=f"habit,{name}")
    streak, d = 0, today
    while mem.fact_get(f"habit:{name}:{d.isoformat()}") is not None:
        streak += 1
        d -= timedelta(days=1)
    return f"«{name}»: отмечено за {today.isoformat()}, серия {streak} дн."


@agent("timer.pomodoro", "Помидорный таймер", "life",
       "Расписание циклов 25/5 с временем начала и конца",
       keywords=("помодоро", "таймер", "pomodoro", "25 минут", "перерыв"),
       examples=("cycles=3 start=10:00",), needs=())
def pomodoro(ctx: Context, text: str):
    params, _ = parse_kv(text)
    cycles = max(1, min(12, int(params.get("cycles", 4))))
    work, rest = int(params.get("work", 25)), int(params.get("rest", 5))
    raw = params.get("start") or datetime.now().strftime("%H:%M")
    hh, mm = map(int, raw.split(":"))
    t = datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
    lines = []
    for i in range(1, cycles + 1):
        end = t + timedelta(minutes=work)
        lines.append(f"  цикл {i}: {t:%H:%M}–{end:%H:%M} работа")
        t = end + timedelta(minutes=rest if i < cycles else 0)
        if i < cycles:
            lines.append(f"          {end:%H:%M}–{t:%H:%M} перерыв")
    return f"Помидоро, старт {raw}:\n" + "\n".join(lines)


@agent("decision.matrix", "Матрица решений", "life",
       "Взвешенно сравнивает варианты по критериям",
       keywords=("решение", "выбери", "сравни варианты", "матрица", "плюсы минусы"),
       examples=("w=0.4,0.3,0.3\nРоутер 8,9,5\nМини-ПК 9,6,8",), needs=())
def decision(ctx: Context, text: str):
    params, rest = parse_kv(text)
    rows = []
    weights = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("w="):
            weights = [float(x) for x in line[2:].replace(",", " ").split()]
            continue
        m = re.match(r"(.+?)\s+([\d.,\s]+)$", line)
        if not m:
            continue
        name = m.group(1).strip()
        scores = [float(x.replace(",", ".")) for x in re.split(r"[,;\s]+", m.group(2)) if x]
        rows.append((name, scores))
    if not rows:
        raise ValueError("формат: 'вариант 8 9 5' по строке, веса w=0.4,0.3,0.3")
    n = len(rows[0][1])
    weights = (weights or [1.0] * n)[:n]
    if len(weights) < n:
        weights += [1.0] * (n - len(weights))
    total_w = sum(weights) or 1.0
    ranked = []
    for name, scores in rows:
        s = sum(sc * w for sc, w in zip(scores, weights)) / total_w
        ranked.append((s, name))
    ranked.sort(reverse=True)
    out = table([[name, f"{s:.2f}"] for s, name in ranked],
                ["вариант", "итог"], align_right={1})
    return out + f"\nпобедитель: {ranked[0][1]} ({ranked[0][0]:.2f})"
