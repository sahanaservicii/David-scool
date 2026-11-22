"""Мелкие утилиты без зависимостей: формат, байты, слаги, парсинг."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

# ---------------------------------------------------------------- время
def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ---------------------------------------------------------------- числа
def human_bytes(n: float, precision: int = 1) -> str:
    n = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024.0 or unit == "TiB":
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.{precision}f} {unit}"
        n /= 1024.0
    return f"{n:.{precision}f} TiB"


def human_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    parts = []
    for name, size in (("д", 86400), ("ч", 3600), ("м", 60), ("с", 1)):
        if seconds >= size:
            parts.append(f"{seconds // size}{name}")
            seconds %= size
    return " ".join(parts) or "0с"


# ---------------------------------------------------------------- текст
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def translit(text: str) -> str:
    out = []
    for ch in text:
        low = ch.lower()
        if low in _TRANSLIT:
            tr = _TRANSLIT[low]
            out.append(tr.capitalize() if ch.isupper() and tr else tr)
        else:
            out.append(ch)
    return "".join(out)


def slugify(text: str, maxlen: int = 60) -> str:
    text = translit(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:maxlen].rstrip("-")


def truncate(text: str, limit: int = 120, ellipsis: str = "…") -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - len(ellipsis))].rstrip() + ellipsis


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


# ---------------------------------------------------------------- безопасность
_SECRET_RE = re.compile(
    r'(?i)([\w.\-]*(?:token|password|passwd|secret|api[_-]?key|ssh_key)[\w.\-]*)'
    r'("?\s*[:=]\s*"?)([^\s",;}]+)'
)


_NESTED_QUANT = re.compile(r"\([^()]*[+*][^()]*\)\s*(?:[+*]|\{\d*,?\d*\})")


def guard_regex(pattern: str) -> None:
    """Отсекает заведомо катастрофические regex (ReDoS) и гигантские шаблоны."""
    if len(pattern) > 300:
        raise ValueError("слишком длинный regex (предел 300)")
    if _NESTED_QUANT.search(pattern):
        raise ValueError("вложенные квантификаторы запрещены (ReDoS)")


def redact(text: str) -> str:
    """Скрывает значения секретов: KEY=value, "key": "value", HASS_TOKEN=..."""
    text = _SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)
    text = re.sub(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}",
                  "***JWT***", text)
    return text


# ---------------------------------------------------------------- вывод
def table(rows, headers=None, align_right=None) -> str:
    rows = [[("" if c is None else str(c)) for c in row] for row in rows]
    if not rows and not headers:
        return "(пусто)"
    width = max(len(r) for r in rows) if rows else 0
    if headers:
        width = max(width, len(headers))
    cols = [0] * width
    for row in rows + ([list(headers)] if headers else []):
        for i, cell in enumerate(row):
            cols[i] = max(cols[i], len(cell))
    align_right = set(align_right or ())
    lines = []
    if headers:
        lines.append("  ".join(h.ljust(cols[i]) for i, h in enumerate(headers)).rstrip())
        lines.append("  ".join("-" * cols[i] for i in range(width)).rstrip())
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            cells.append(cell.rjust(cols[i]) if i in align_right else cell.ljust(cols[i]))
        lines.append("  ".join(cells).rstrip())
    return "\n".join(lines)


def bullets(items) -> str:
    return "\n".join(f"- {i}" for i in items)


def kv(pairs) -> str:
    width = max((len(str(k)) for k, _ in pairs), default=0)
    return "\n".join(f"{str(k).ljust(width)} : {v}" for k, v in pairs)


# ---------------------------------------------------------------- парсинг
def parse_kv(text: str):
    """'host=1.2.3.4 port=22 остаток' -> ({'host': '1.2.3.4', 'port': '22'}, 'остаток')."""
    params, words = {}, []
    for token in text.split():
        if "=" in token:
            k, v = token.split("=", 1)
            params[k.strip().lower()] = v.strip('"\'')
        else:
            words.append(token)
    return params, " ".join(words)


_PARAM_RE = re.compile(
    r'(?<!\S)([^\W\d]\w*)=("([^"]*)"|\'([^\']*)\'|(\S+))', re.UNICODE)


def parse_params(text: str):
    """Как parse_kv, но сохраняет переводы строк и понимает "значение в кавычках"."""
    params: dict[str, str] = {}

    def repl(m):
        key = m.group(1).lower()
        val = (m.group(3) if m.group(3) is not None
               else m.group(4) if m.group(4) is not None else m.group(5))
        params[key] = val
        return ""

    rest = _PARAM_RE.sub(repl, text)
    rest = re.sub(r"[ \t]{2,}", " ", rest)
    return params, rest.strip("\n").strip()


def to_int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def split_csv(text: str):
    """Простой CSV-разбор с поддержкой кавычек."""
    import csv
    import io
    return [row for row in csv.reader(io.StringIO(text.strip()))]


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
