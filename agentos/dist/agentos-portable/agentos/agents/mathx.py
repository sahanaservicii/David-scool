"""Математика, сети-калькулятор, время, единицы, случайность."""
from __future__ import annotations

import ast
import math as _math
import operator
import random as _random
import re
import secrets
import statistics
import uuid as _uuid
from datetime import datetime, date, timedelta, timezone

from ..core import Context, agent
from ..utils import kv, parse_kv, table

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_FUNCS = {
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
    "sqrt": _math.sqrt, "log": _math.log, "log10": _math.log10,
    "exp": _math.exp, "sin": _math.sin, "cos": _math.cos, "tan": _math.tan,
    "floor": _math.floor, "ceil": _math.ceil,
    "fact": lambda n: _math.factorial(int(n)) if 0 <= int(n) <= 10000
    else (_ for _ in ()).throw(ValueError("fact: предел 10000")),
}
_CONSTS = {"pi": _math.pi, "e": _math.e, "tau": _math.tau}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) is ast.Pow:
        base, exp = _eval(node.left), _eval(node.right)
        if abs(exp) > 1000:
            raise ValueError("слишком большая степень")
        return base ** exp
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS and not node.keywords):
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    raise ValueError("выражение содержит запрещённые элементы")


@agent("math.calc", "Калькулятор", "math",
       "Считает арифметику и функции (sqrt, log, sin…) без eval",
       keywords=("посчитай", "калькулятор", "calc", "сколько будет", "вычисли"),
       examples=("2*(3+4)^2 / 7",), needs=())
def calc(ctx: Context, text: str):
    expr = (text or "").strip()
    # выбрасываем русские слова-обёртки («посчитай», «сколько будет»)
    expr = re.sub(r"[а-яА-ЯёЁ]+", " ", expr)
    expr = expr.replace("×", "*").replace("÷", "/").replace(",", ".")
    expr = re.sub(r"\s+", "", expr)
    if not expr:
        raise ValueError("пустое выражение")
    expr = expr.replace("^", "**")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"синтаксис: {exc.msg}")
    value = _eval(tree)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{expr} = {value}"


@agent("math.percent", "Проценты", "math",
       "Считает процент от числа, долю и изменение в процентах",
       keywords=("процент", "percent", "доля", "скидка", "на сколько процентов"),
       examples=("p=15 of=2400",), needs=())
def percent(ctx: Context, text: str):
    params, rest = parse_kv(text)
    p, of = params.get("p"), params.get("of")
    if not (p and of):
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*%\s*(?:от|of)\s*(\d+(?:[.,]\d+)?)", rest, re.I)
        if not m:
            raise ValueError("формат: p=15 of=2400")
        p, of = m.group(1), m.group(2)
    p, of = float(p.replace(",", ".")), float(of.replace(",", "."))
    part = of * p / 100
    return kv([("процент", f"{p:g}%"), ("от числа", f"{of:g}"),
               ("результат", f"{part:g}"),
               ("число + процент", f"{of + part:g}"),
               ("число − процент", f"{of - part:g}")])


@agent("math.stats", "Статистика чисел", "math",
       "Среднее, медиана, мода, ст. отклонение, min/max по списку",
       keywords=("статистика", "среднее", "медиана", "отклонение", "разброс"),
       examples=("12 15 11 18 20 15 14",), needs=())
def stats(ctx: Context, text: str):
    nums = [float(x.replace(",", ".")) for x in re.findall(r"-?\d+(?:[.,]\d+)?", text)]
    if not nums:
        raise ValueError("нужен список чисел")
    return kv([("n", len(nums)), ("сумма", f"{sum(nums):g}"),
               ("среднее", f"{statistics.mean(nums):.3g}"),
               ("медиана", f"{statistics.median(nums):.3g}"),
               ("мода", f"{statistics.mode(nums):.3g}" if len(set(nums)) < len(nums) else "—"),
               ("ст. отклонение", f"{statistics.pstdev(nums):.3g}"),
               ("min / max", f"{min(nums):g} / {max(nums):g}")])


@agent("math.base", "Системы счисления", "math",
       "Переводит число между базами 2–36",
       keywords=("система счисления", "hex", "bin", "base", "переведи число"),
       examples=("value=255 to=16",), needs=())
def base(ctx: Context, text: str):
    params, rest = parse_kv(text)
    raw = params.get("value") or rest.strip()
    to = int(params.get("to", 10))
    if not raw:
        raise ValueError("нужно value=... to=16")
    value = int(raw, 0) if raw.lower().startswith(("0x", "0b", "0o")) else int(raw)
    if to == 10:
        return f"{raw} → {value} (10)"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    n, out = abs(value), ""
    while n:
        n, r = divmod(n, to)
        out = digits[r] + out
    out = out or "0"
    return f"{raw} → {'-' if value < 0 else ''}{out} (база {to})"


_UNITS = {
    "bytes": {"b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4,
              "kib": 1024, "mib": 1024**2, "gib": 1024**3, "tib": 1024**4},
    "time": {"ms": 0.001, "s": 1, "min": 60, "h": 3600, "d": 86400},
    "length": {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000, "mi": 1609.344,
               "ft": 0.3048, "in": 0.0254},
    "mass": {"g": 1, "kg": 1000, "lb": 453.592, "oz": 28.3495, "t": 1_000_000},
}


@agent("math.unit", "Единицы", "math",
       "Конвертирует байты, время, длину и вес",
       keywords=("конвертируй", "единицы", "гигабайты", "переведи", "unit"),
       examples=("10 GiB to MB",), needs=())
def unit(ctx: Context, text: str):
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)\s*(?:to|в)\s*([a-zA-Z]+)", text)
    if not m:
        raise ValueError("формат: 10 GiB to MB")
    value, src, dst = float(m.group(1).replace(",", ".")), m.group(2).lower(), m.group(3).lower()
    for table_ in _UNITS.values():
        if src in table_ and dst in table_:
            out = value * table_[src] / table_[dst]
            return f"{value:g} {src} = {out:.4g} {dst}"
    if {src, dst} <= {"c", "f", "k"}:
        c = value if src == "c" else (value - 32) * 5 / 9 if src == "f" else value - 273.15
        res = {"c": c, "f": c * 9 / 5 + 32, "k": c + 273.15}[dst]
        return f"{value:g}°{src.upper()} = {res:.2f}°{dst.upper()}"
    raise ValueError(f"не знаю пару {src}→{dst}")


@agent("math.date", "Даты", "math",
       "Разница между датами, прибавление дней, день недели",
       keywords=("дата", "сколько дней", "date", "срок", "прибавь дни", "день недели"),
       examples=("date=2026-11-15 add=30",), needs=())
def date_tool(ctx: Context, text: str):
    params, rest = parse_kv(text)
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
    if len(dates) >= 2:
        a, b = date.fromisoformat(dates[0]), date.fromisoformat(dates[1])
        delta = (b - a).days
        return kv([("от", a.isoformat()), ("до", b.isoformat()),
                   ("дней", delta), ("недель", f"{delta / 7:.1f}"),
                   ("день недели", b.strftime("%A"))])
    raw = params.get("date") or (dates[0] if dates else None) or date.today().isoformat()
    d = date.fromisoformat(raw)
    add = int(params.get("add", 0))
    d2 = d + timedelta(days=add)
    return kv([("дата", d.isoformat()), ("день недели", d.strftime("%A")),
               ("плюс дней", add), ("результат", d2.isoformat()),
               ("день недели результата", d2.strftime("%A"))])


@agent("math.tz", "Часовые пояса", "math",
       "Переводит время между часовыми поясами (zoneinfo, офлайн)",
       keywords=("часовой пояс", "время", "timezone", "переведи время", "utc"),
       examples=("12:00 Europe/Moscow to Asia/Tokyo",), needs=())
def tz(ctx: Context, text: str):
    from zoneinfo import ZoneInfo
    m = re.search(r"(\d{1,2}:\d{2})\s+([\w/+-]+)\s*(?:to|в)\s*([\w/+-]+)", text)
    if m:
        hm, src, dst = m.groups()
        hour, minute = map(int, hm.split(":"))
        today = datetime.now(ZoneInfo(src)).date()
        base = datetime(today.year, today.month, today.day, hour, minute, tzinfo=ZoneInfo(src))
    else:
        pairs = re.findall(r"(?:Europe|Asia|America|Africa|Australia|UTC)[\w/+-]*", text)
        if len(pairs) < 2:
            raise ValueError("формат: 12:00 Europe/Moscow to Asia/Tokyo")
        base = datetime.now(ZoneInfo(pairs[0]))
        dst = pairs[1]
    conv = base.astimezone(ZoneInfo(dst))
    return (f"{base:%Y-%m-%d %H:%M %Z} ({base.tzinfo}) = "
            f"{conv:%Y-%m-%d %H:%M %Z} ({dst})")


@agent("math.cron", "Разбор cron", "math",
       "Объясняет cron-выражение человеческим языком",
       keywords=("cron", "крон", "расписание", "каждые", "по расписанию"),
       examples=("*/15 3 * * 1-5",), needs=())
def cron(ctx: Context, text: str):
    fields = (text or "").split()
    if len(fields) not in (5, 6):
        raise ValueError("нужно 5 полей: мин час день месяц день_недели")
    if len(fields) == 6:
        fields = fields[1:]
    minute, hour, dom, month, dow = fields
    def fmt(v, every, unit):
        if v == "*":
            return f"каждый {every}"
        if v.startswith("*/"):
            return f"каждые {v[2:]} {unit}"
        if "," in v:
            return f"{unit} {v}"
        if "-" in v:
            return f"{unit} {v.replace('-', '–')}"
        return f"{unit} {v}"
    days = {"0": "вс", "1": "пн", "2": "вт", "3": "ср", "4": "чт", "5": "пт",
            "6": "сб", "7": "вс"}
    dow_txt = "любой день" if dow == "*" else (
        "по " + ", ".join(days.get(x, x) for x in re.split(r"[,\-]", dow)))
    return (f"cron: {' '.join(fields)}\n"
            f"минуты: {fmt(minute, 'минуту', 'мин')}\n"
            f"часы: {fmt(hour, 'час', 'ч')}\n"
            f"день месяца: {fmt(dom, 'день', 'день')}\n"
            f"месяц: {fmt(month, 'месяц', 'мес')}\n"
            f"день недели: {dow_txt}")


@agent("math.factor", "Разложение на множители", "math",
       "Раскладывает число на простые множители и считает делители",
       keywords=("множители", "factor", "простое число", "делители", "разложи"),
       examples=("360",), needs=())
def factor(ctx: Context, text: str):
    import re as _re
    m = _re.search(r"\d+", text)
    if not m:
        raise ValueError("нужно целое число")
    n = int(m.group())
    if n < 2:
        return f"{n}: не раскладывается"
    if n > 10 ** 12:
        raise ValueError("слишком большое число (предел 10^12)")
    x, factors = n, []
    d = 2
    while d * d <= x:
        while x % d == 0:
            factors.append(d)
            x //= d
        d += 1 if d == 2 else 2
    if x > 1:
        factors.append(x)
    divisors = 0
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            divisors += 1 if i * i == n else 2
    return kv([("число", n), ("множители", " × ".join(map(str, factors))),
               ("делителей", divisors + 2),
               ("простое", "да" if len(factors) == 1 else "нет")])


@agent("math.uuid", "UUID", "math",
       "Генерирует UUID4 (n штук) для задач и конфигов",
       keywords=("uuid", "идентификатор", "guid", "сгенерируй id"),
       examples=("3",), needs=())
def uuid_agent(ctx: Context, text: str):
    n = int(text.strip()) if text.strip().isdigit() else 1
    n = max(1, min(50, n))
    return "\n".join(str(_uuid.uuid4()) for _ in range(n))


@agent("math.random", "Случайность", "math",
       "Бросок кубиков, выбор из списка, криптостойкий токен",
       keywords=("случайное", "кубик", "dice", "выбери", "токен", "random"),
       examples=("dice=2d6",), needs=())
def random_agent(ctx: Context, text: str):
    params, rest = parse_kv(text)
    if "dice" in params:
        m = re.fullmatch(r"(\d*)d(\d+)", params["dice"].lower())
        if not m:
            raise ValueError("формат dice=2d6")
        count, sides = int(m.group(1) or 1), int(m.group(2))
        count = max(1, min(50, count))
        rolls = [_random.randint(1, sides) for _ in range(count)]
        return f"{count}d{sides}: {rolls} = {sum(rolls)}"
    if "choice" in params:
        options = [o.strip() for o in params["choice"].split(",") if o.strip()]
        if not options:
            raise ValueError("пустой список choice")
        return f"выбор: {_random.choice(options)} (из {len(options)})"
    if "token" in params:
        n = int(params["token"]) if params["token"].isdigit() else 32
        return secrets.token_urlsafe(max(8, min(128, n)))
    return f"монетка: {_random.choice(['орёл', 'решка'])}"
