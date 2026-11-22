"""Текстовые мини-агенты: без LLM, детерминированно и воспроизводимо."""
from __future__ import annotations

import base64
import collections
import csv
import difflib
import io
import json
import re
import textwrap
import urllib.parse

from ..core import Context, agent
from ..tools import read_text
from ..utils import (guard_regex, kv, parse_params, slugify, table,
                     translit, truncate)

STOP = set("""и в во не что он на я с со как а то все она так его но да ты к у же
вы за бы по только ее мне было вот от меня еще нет о из ему теперь когда даже ну
ли если уже или ни быть был него до вас нибудь опять уж вам ведь там потом себя
ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без
будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой совсем
ним здесь этом один почти мой тем чтобы нее сейчас были куда зачем всех никогда
можно при наконец два об другой хоть после над больше тот через эти нас про всего
них какая много разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть
том нельзя такой им более всегда конечно всю между the a an and or of to in is are
was were be been it this that for on with as at by from not""".split())


def _source(ctx: Context, text: str):
    """(текст, параметры). Переводы строк сохраняются."""
    params, body = parse_params(text)
    path = params.get("файл") or params.get("file")
    if path:
        return read_text(ctx, path), params
    return body, params


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+|\n{2,}", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _words(text: str) -> list[str]:
    return re.findall(r"[\w'-]+", text.lower())


@agent("txt.stats", "Статистика текста", "text",
       "Символы, слова, предложения, уникальность и время чтения",
       keywords=("статистика текста", "сколько слов", "символы", "объём", "wc"),
       examples=("Домовой следит за сетью. Он любит порядок и тишину.",), needs=())
def stats(ctx: Context, text: str):
    src, _ = _source(ctx, text)
    words = _words(src)
    sents = _sentences(src)
    unique = len(set(words))
    minutes = len(words) / 180
    return kv([
        ("символов", len(src)), ("без пробелов", len(re.sub(r"\s", "", src))),
        ("слов", len(words)), ("уникальных", unique),
        ("предложений", len(sents)),
        ("абзацев", len([p for p in src.split("\n\n") if p.strip()])),
        ("средняя длина слова", f"{sum(map(len, words)) / len(words):.1f}" if words else "0"),
        ("время чтения", f"{max(1, round(minutes))} мин" if src else "0 мин"),
    ])


@agent("txt.summary", "Краткое изложение", "text",
       "Экстрактивное резюме: выбирает самые информативные предложения",
       keywords=("сократи", "summary", "резюме", "выжимка", "о чём текст", "кратко"),
       examples=("Сеть работает стабильно. Роутер отвечает по SSH. Камеры изолированы. "
                 "Бэкап делается nightly. Home Assistant отложен до настройки WireGuard.",),
       needs=())
def summary(ctx: Context, text: str):
    src, params = _source(ctx, text)
    sents = _sentences(src)
    if len(sents) <= 2:
        return src.strip() or "(пусто)"
    n = int(params.get("n", max(1, round(len(sents) * 0.3))))
    n = min(n, len(sents))
    words = [w for w in _words(src) if w not in STOP and len(w) > 2]
    freq = collections.Counter(words)
    if freq:
        top = max(freq.values())
        for k in freq:
            freq[k] /= top
    scored = []
    for idx, s in enumerate(sents):
        ws = [w for w in _words(s) if w not in STOP]
        if not ws:
            continue
        scored.append((sum(freq.get(w, 0) for w in ws) / (len(ws) ** 0.6), idx))
    chosen = sorted(idx for _, idx in sorted(scored, reverse=True)[:n])
    return " ".join(sents[i] for i in chosen)


@agent("txt.keywords", "Ключевые слова", "text",
       "Топ значимых слов и фраз текста (TF, без стоп-слов)",
       keywords=("ключевые слова", "keywords", "теги", "о чём", "термины"),
       examples=("Роутер OpenWrt, камеры XMEye, бэкап конфигов роутера и Home Assistant.",),
       needs=())
def keywords(ctx: Context, text: str):
    src, params = _source(ctx, text)
    n = int(params.get("n", 10))
    words = [w for w in _words(src) if w not in STOP and len(w) > 2 and not w.isdigit()]
    single = collections.Counter(words)
    bigrams = collections.Counter()
    for a, b in zip(words, words[1:]):
        bigrams[f"{a} {b}"] += 1
    rows = [[w, c] for w, c in single.most_common(n)]
    out = table(rows, ["термин", "частота"], align_right={1})
    top_bi = [(p, c) for p, c in bigrams.most_common(3) if c > 1]
    if top_bi:
        out += "\nфразы: " + ", ".join(f"{p} ({c})" for p, c in top_bi)
    return out


@agent("txt.readability", "Читаемость", "text",
       "Оценка сложности текста (адаптированный индекс Флеша для русского)",
       keywords=("читаемость", "сложность", "flesch", "понятность", "уровень"),
       examples=("Сегодня сеть работает хорошо. Роутер отвечает быстро.",), needs=())
def readability(ctx: Context, text: str):
    src, _ = _source(ctx, text)
    words = _words(src)
    sents = _sentences(src) or [src]
    vowels = "аеёиоуыэюяaeiouy"
    syllables = sum(1 for c in src.lower() if c in vowels) or 1
    if not words:
        return "пустой текст"
    asl = len(words) / max(1, len(sents))
    asw = syllables / len(words)
    score = 206.835 - 1.3 * asl - 60.1 * asw
    grade = ("очень просто" if score > 80 else "просто" if score > 60 else
             "средне" if score > 50 else "сложно" if score > 30 else "очень сложно")
    return kv([("слов в предложении", f"{asl:.1f}"),
               ("слогов в слове", f"{asw:.2f}"),
               ("индекс", f"{score:.1f}"), ("оценка", grade)])


@agent("txt.diff", "Сравнение текстов", "text",
       "Унифицированный diff двух текстов: блоки через строку '---' или файлы",
       keywords=("diff", "сравни", "разница", "отличия", "что изменилось"),
       examples=("version 1\ntimeout 10\n---\nversion 2\ntimeout 30",), needs=())
def diff(ctx: Context, text: str):
    params, body = parse_params(text)
    a, b = params.get("a"), params.get("b")
    if a and b:
        left, right = a, b
    else:
        raw = body if body else text
        if "\n---\n" not in raw:
            raise ValueError("нужны два блока через строку '---' или a=/b=")
        left, right = raw.split("\n---\n", 1)
    if a and a.startswith("/"):
        try:
            left = read_text(ctx, a)
        except Exception:
            pass
    if b and b.startswith("/"):
        try:
            right = read_text(ctx, b)
        except Exception:
            pass
    lines = list(difflib.unified_diff(left.splitlines(), right.splitlines(),
                                      "до", "после", lineterm=""))
    return "\n".join(lines) if lines else "различий нет"


@agent("txt.dedupe", "Удаление дублей", "text",
       "Убирает повторяющиеся строки, сохраняя порядок",
       keywords=("дубли", "duplicates", "повторы", "уникальные строки", "uniq"),
       examples=("яблоко\nгруша\nяблоко\nслива",), needs=())
def dedupe(ctx: Context, text: str):
    src, _ = _source(ctx, text)
    lines = src.splitlines()
    seen, out = set(), []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return "\n".join(out) + f"\n\nбыло {len(lines)}, стало {len(out)}"


@agent("txt.sort", "Сортировка строк", "text",
       "Сортирует строки: по алфавиту, числам, в обратном порядке",
       keywords=("сортировка", "sort", "отсортируй", "по порядку", "по возрастанию"),
       examples=("10\n2\n33\n1",), needs=())
def sort_lines(ctx: Context, text: str):
    src, params = _source(ctx, text)
    lines = [l for l in src.splitlines() if l.strip()]
    reverse = params.get("reverse") in ("1", "да", "true", "yes")
    numeric = params.get("numeric") in ("1", "да", "true", "yes") or all(
        re.fullmatch(r"-?\d+(\.\d+)?", l.strip()) for l in lines if l.strip())
    key = (lambda s: float(s)) if numeric else (lambda s: s.lower())
    try:
        lines.sort(key=key, reverse=reverse)
    except ValueError:
        lines.sort(reverse=reverse)
    return "\n".join(lines)


@agent("txt.extract", "Извлечение по regex", "text",
       "Достаёт из текста всё, что совпало с регулярным выражением",
       keywords=("regex", "извлеки", "найди", "шаблон", "парсинг"),
       examples=("pattern=\\d+ заказы 12, 340 и 5",), needs=())
def extract(ctx: Context, text: str):
    params, body = parse_params(text)
    pat = params.get("pattern") or params.get("p")
    if not pat:
        raise ValueError("нужен pattern=...")
    guard_regex(pat)
    try:
        found = re.findall(pat, body)
    except re.error as exc:
        raise ValueError(f"плохой regex: {exc}")
    flat = [f if isinstance(f, str) else " ".join(f) for f in found]
    if not flat:
        return "совпадений нет"
    return f"найдено {len(flat)}:\n" + "\n".join(flat[:100])


@agent("txt.replace", "Замена по regex", "text",
       "Заменяет совпадения регулярного выражения в тексте",
       keywords=("замени", "replace", "regex замена", "подставь"),
       examples=("pattern=кот repl=пёс кот и ещё кот",), needs=())
def replace(ctx: Context, text: str):
    params, body = parse_params(text)
    pat, repl = params.get("pattern"), params.get("repl", "")
    if not pat:
        raise ValueError("нужен pattern=... и repl=...")
    guard_regex(pat)
    try:
        return re.sub(pat, repl, body)
    except re.error as exc:
        raise ValueError(f"плохой regex: {exc}")


@agent("txt.csv2json", "CSV → JSON", "text",
       "Преобразует CSV (с заголовком) в массив JSON-объектов",
       keywords=("csv", "json", "конвертируй", "таблица в json"),
       examples=("ip,port,role\n192.168.1.1,22,router\n192.168.1.10,80,camera",), needs=())
def csv2json(ctx: Context, text: str):
    src, _ = _source(ctx, text)
    if not src.strip():
        raise ValueError("пустой CSV")
    sample = src.splitlines()[0]
    delim = max((",", ";", "\t"), key=sample.count)
    reader = list(csv.DictReader(io.StringIO(src), delimiter=delim))
    return json.dumps(reader, ensure_ascii=False, indent=2)


@agent("txt.json2csv", "JSON → CSV", "text",
       "Преобразует массив JSON-объектов в CSV",
       keywords=("json в csv", "json2csv", "выгрузи таблицу", "csv"),
       examples=('[{"ip":"192.168.1.1","port":22},{"ip":"192.168.1.10","port":80}]',),
       needs=())
def json2csv(ctx: Context, text: str):
    src, _ = _source(ctx, text)
    data = json.loads(src)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data:
        raise ValueError("нужен непустой массив объектов")
    fields = list(dict.fromkeys(k for row in data for k in row))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in data:
        writer.writerow({k: row.get(k, "") for k in fields})
    return buf.getvalue().strip()


@agent("txt.json", "JSON: формат и проверка", "text",
       "Проверяет, форматирует или минифицирует JSON",
       keywords=("json", "формат", "проверь json", "minify", "pretty"),
       examples=('{"b":1,"a":[1,2,3]}',), needs=())
def json_tool(ctx: Context, text: str):
    src, params = _source(ctx, text)
    try:
        obj = json.loads(src)
    except ValueError as exc:
        return f"невалидный JSON: {exc}"
    if params.get("min"):
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


@agent("txt.slug", "Slug", "text",
       "Делает безопасный slug/имя файла из заголовка на любом языке",
       keywords=("slug", "имя файла", "транслит", "ссылку", "url"),
       examples=("Настройка WireGuard в домашней сети",), needs=())
def slug(ctx: Context, text: str):
    src, _ = _source(ctx, text)
    src = src.strip()
    return f"slug: {slugify(src)}\nтранслит: {translit(src)}"


@agent("txt.base64", "Base64", "text",
       "Кодирует или декодирует Base64 (mode=decode)",
       keywords=("base64", "кодируй", "декодируй", "шифр текста"),
       examples=("mode=encode привет мир",), needs=())
def b64(ctx: Context, text: str):
    src, params = _source(ctx, text)
    if params.get("mode") == "decode":
        try:
            return base64.b64decode(src + "=" * (-len(src) % 4)).decode("utf-8", "replace")
        except Exception as exc:
            raise ValueError(f"не декодируется: {exc}")
    return base64.b64encode(src.encode("utf-8")).decode()


@agent("txt.urlencode", "URL-кодирование", "text",
       "Кодирует или декодирует строку для URL (mode=decode)",
       keywords=("urlencode", "url", "процентное кодирование", "query"),
       examples=("mode=encode привет мир&x=1",), needs=())
def urlencode(ctx: Context, text: str):
    src, params = _source(ctx, text)
    if params.get("mode") == "decode":
        return urllib.parse.unquote_plus(src)
    return urllib.parse.quote_plus(src)


@agent("txt.case", "Регистр и стиль", "text",
       "upper/lower/title/snake/camel/kebab для строки",
       keywords=("регистр", "case", "snake", "camel", "kebab", "title", "заглавные"),
       examples=("mode=snake Моя Новая Переменная",), needs=())
def case(ctx: Context, text: str):
    src, params = _source(ctx, text)
    mode = (params.get("mode") or "title").lower()
    words = re.findall(r"[\w']+", src)
    if mode == "upper":
        return src.upper()
    if mode == "lower":
        return src.lower()
    if mode == "title":
        return src.title()
    if mode == "snake":
        return "_".join(w.lower() for w in words)
    if mode == "kebab":
        return "-".join(w.lower() for w in words)
    if mode in ("camel", "pascal"):
        parts = [w.capitalize() for w in words]
        return "".join(parts) if mode == "pascal" else (
            parts[0].lower() + "".join(parts[1:]) if parts else "")
    raise ValueError("mode: upper|lower|title|snake|kebab|camel")


@agent("txt.wrap", "Перенос строк", "text",
       "Разбивает длинный текст на строки заданной ширины",
       keywords=("перенос", "wrap", "ширина", "строки", "формат"),
       examples=("width=30 Домовой следит за порядком в домашней сети и пишет отчёты",),
       needs=())
def wrap(ctx: Context, text: str):
    src, params = _source(ctx, text)
    width = int(params.get("width", 80))
    return "\n".join(textwrap.wrap(src, width=max(10, width)))


@agent("txt.clean", "Очистка текста", "text",
       "Убирает лишние пробелы, пустые строки и мусорные символы",
       keywords=("очисти", "clean", "пробелы", "нормализуй", "убери мусор"),
       examples=("  привет   мир  \n\n\n  как   дела  ",), needs=())
def clean(ctx: Context, text: str):
    src, _ = _source(ctx, text)
    src = src.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    src = re.sub(r"[ \u00a0]+", " ", src)
    src = re.sub(r" *\n *", "\n", src)
    src = re.sub(r"\n{3,}", "\n\n", src)
    return src.strip()


@agent("txt.template", "Шаблон", "text",
       "Подставляет значения в шаблон {{ключ}} из пар key=value",
       keywords=("шаблон", "template", "подстановка", "письмо", "текст по форме"),
       examples=('шаблон="Привет, {{имя}}! Твой IP {{ip}}." имя=Иван ip=192.168.1.5',),
       needs=())
def template(ctx: Context, text: str):
    params, _ = parse_params(text)
    tpl = params.get("шаблон") or params.get("template")
    if not tpl:
        raise ValueError("нужен шаблон=\"...\" со вставками {{ключ}}")
    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}",
                  lambda m: params.get(m.group(1).strip(), m.group(0)), tpl)
