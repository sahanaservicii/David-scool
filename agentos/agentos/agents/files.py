"""Файлы и каталоги: чтение, поиск, размеры, архивы, типы, хэши."""
from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import tarfile
from pathlib import Path

from ..core import Context, agent
from ..tools import read_text, resolve_path, write_text, ToolError
from ..utils import (guard_regex, human_bytes, kv, parse_kv, redact,
                     table, truncate)

_SECRET_HINT = re.compile(r"(secret|token|passw|credential|\.env|id_rsa|\.key)", re.I)


def _walk(base: Path, limit: int = 20000):
    n = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in
                       ("__pycache__", ".git", "node_modules")]
        for name in filenames:
            n += 1
            if n > limit:
                return
            yield Path(dirpath) / name


@agent("fs.ls", "Список файлов", "files",
       "Подробный список каталога: размер, дата, права",
       keywords=("ls", "список файлов", "что в папке", "каталог", "содержимое"),
       examples=("path=@homelab",), needs=())
def ls(ctx: Context, text: str):
    params, rest = parse_kv(text)
    raw = params.get("path") or rest or "."
    base = resolve_path(ctx, raw)
    if not base.is_dir():
        raise ToolError("нужен каталог")
    rows = []
    for p in sorted(base.iterdir())[:200]:
        try:
            st = p.stat()
        except OSError:
            continue
        rows.append(["d" if p.is_dir() else "-", f"{st.st_mode & 0o777:o}",
                     human_bytes(st.st_size), p.name])
    return f"{base}\n" + table(rows, ["тип", "права", "размер", "имя"],
                               align_right={2})


@agent("fs.tree", "Дерево каталога", "files",
       "Показывает структуру каталога деревом (глубина ограничена)",
       keywords=("дерево", "tree", "структура", "схема каталогов"),
       examples=("path=@app depth=2",), needs=())
def tree(ctx: Context, text: str):
    params, rest = parse_kv(text)
    base = resolve_path(ctx, params.get("path") or rest or ".")
    depth = max(0, min(6, int(params.get("depth", 2))))
    lines = [base.name + "/"]

    def walk(d: Path, prefix: str, level: int):
        if level > depth:
            return
        try:
            items = sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name))
        except OSError:
            return
        items = [i for i in items if i.name not in ("__pycache__", ".git", "node_modules")]
        for i, item in enumerate(items[:30]):
            last = i == len(items[:30]) - 1
            lines.append(prefix + ("└── " if last else "├── ") + item.name
                         + ("/" if item.is_dir() else ""))
            if item.is_dir():
                walk(item, prefix + ("    " if last else "│   "), level + 1)

    walk(base, "", 1)
    return "\n".join(lines[:200])


@agent("fs.find", "Поиск файлов", "files",
       "Ищет файлы по маске имени, расширению и минимальному размеру",
       keywords=("найди файл", "find", "поиск", "маска", "*.log", "где лежит"),
       examples=("path=@app pattern=*.py",), needs=())
def find(ctx: Context, text: str):
    params, rest = parse_kv(text)
    base = resolve_path(ctx, params.get("path") or ".")
    pattern = params.get("pattern") or params.get("mask") or "*"
    min_size = int(params.get("min", 0))
    rows = []
    for p in _walk(base):
        if fnmatch.fnmatch(p.name.lower(), pattern.lower()):
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if size >= min_size:
                rows.append([truncate(str(p.relative_to(base)), 70), human_bytes(size)])
        if len(rows) >= 60:
            break
    if not rows:
        return f"по маске {pattern} в {base} ничего не найдено"
    return table(rows, ["файл", "размер"], align_right={1}) + f"\nвсего: {len(rows)}"


@agent("fs.du", "Размеры каталогов", "files",
       "Считает размер подкаталогов и показывает топ",
       keywords=("сколько занимает", "du", "размер", "место", "диск"),
       examples=("path=@app depth=1",), needs=())
def du(ctx: Context, text: str):
    params, rest = parse_kv(text)
    base = resolve_path(ctx, params.get("path") or rest or ".")
    totals = {}
    for p in _walk(base, limit=50000):
        try:
            size = p.stat().st_size
        except OSError:
            continue
        rel = p.relative_to(base)
        key = rel.parts[0] if len(rel.parts) > 1 else "(файлы)"
        totals[key] = totals.get(key, 0) + size
    rows = [[k, human_bytes(v)] for k, v in
            sorted(totals.items(), key=lambda x: -x[1])[:15]]
    total = sum(totals.values())
    return table(rows, ["каталог", "размер"], align_right={1}) + \
        f"\nитого: {human_bytes(total)}"


@agent("fs.large", "Крупные файлы", "files",
       "Находит самые большие файлы в каталоге",
       keywords=("большие файлы", "крупные", "что занимает место", "large"),
       examples=("path=@app top=5",), needs=())
def large(ctx: Context, text: str):
    params, rest = parse_kv(text)
    base = resolve_path(ctx, params.get("path") or rest or ".")
    n = max(1, min(100, int(params.get("top", 10))))
    found = []
    for p in _walk(base):
        try:
            found.append((p.stat().st_size, p))
        except OSError:
            continue
        if len(found) > 20000:
            break
    found.sort(reverse=True)
    rows = [[human_bytes(s), truncate(str(p), 80)] for s, p in found[:n]]
    return table(rows, ["размер", "файл"], align_right={0})


def _path_arg(text: str, params: dict) -> str:
    """Достаёт путь из файл=/path= или первого токена с / или расширением."""
    for key in ("файл", "file", "path", "путь"):
        if params.get(key):
            return params[key]
    for tok in text.split():
        if "/" in tok or tok.startswith(".") or re.search(r"\.\w{1,5}$", tok):
            return tok.strip(",;")
    return ""


@agent("fs.tail", "Хвост файла", "files",
       "Показывает последние строки файла (логи)",
       keywords=("tail", "хвост", "последние строки", "лог", "что в конце"),
       examples=("файл=@homelab/CHANGELOG.md n=8",), needs=())
def tail(ctx: Context, text: str):
    params, rest = parse_kv(text)
    path = _path_arg(text, params)
    if not path:
        raise ValueError("нужен файл: run fs.tail \"файл=/путь/к/логу n=20\"")
    n = int(params.get("n", 20))
    src = read_text(ctx, path, limit=2_000_000)
    return "\n".join(src.splitlines()[-n:])


@agent("fs.grep", "Поиск по содержимому", "files",
       "Ищет регулярное выражение в файлах каталога",
       keywords=("grep", "найди в файлах", "поиск по тексту", "содержимое", "regex"),
       examples=("path=@homelab pattern=def cmd_",), needs=())
def grep(ctx: Context, text: str):
    params, rest = parse_kv(text)
    base = resolve_path(ctx, params.get("path") or ".")
    pattern = params.get("pattern") or rest.strip()
    if not pattern:
        raise ValueError("нужен pattern=...")
    guard_regex(pattern)
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"плохой regex: {exc}")
    hits = []
    for p in _walk(base):
        if p.suffix in (".png", ".jpg", ".zip", ".gz", ".so", ".bin", ".sqlite"):
            continue
        try:
            if p.stat().st_size > 2_000_000:
                continue
            for n, line in enumerate(p.read_text("utf-8", errors="replace").splitlines(), 1):
                if rx.search(line):
                    hits.append([p.name, n, redact(line.strip())[:90]])
                    if len(hits) >= 60:
                        break
        except OSError:
            continue
        if len(hits) >= 60:
            break
    if not hits:
        return f"совпадений нет ({pattern})"
    return table(hits, ["файл", "стр", "строка"], align_right={1})


@agent("fs.read", "Чтение файла", "files",
       "Читает текстовый файл, скрывая секреты в подозрительных файлах",
       keywords=("прочитай", "cat", "покажи файл", "содержимое файла", "открой"),
       examples=("файл=@homelab/homelab.json",), needs=())
def read(ctx: Context, text: str):
    params, _ = parse_kv(text)
    raw = _path_arg(text, params)
    if not raw:
        raise ValueError("нужен файл: run fs.read \"файл=/путь/к/файлу\"")
    src = read_text(ctx, raw)
    return redact(src)[:12000]


@agent("fs.write", "Запись файла", "files",
       "Пишет текст в data/ или out/ (в dry-run только показывает план)",
       keywords=("запиши", "создай файл", "сохрани", "write", "в файл"),
       examples=("path=out/note.txt text=привет",), needs=("fs-write"), tags=("write",))
def write(ctx: Context, text: str):
    params, rest = parse_kv(text)
    path = params.get("path") or params.get("файл")
    content = params.get("text") or rest
    if not path:
        raise ValueError("нужен path=out/имя.txt")
    if ctx.dry_run:
        return f"dry-run: записать {len(content)} симв. в {path} (--live)"
    p = write_text(ctx, path, content)
    return f"записано: {p} ({len(content)} симв.)"


@agent("fs.cksum", "Контрольная сумма файла", "files",
       "SHA-256 и размер файла или набора по маске",
       keywords=("чексумма", "cksum", "sha256 файла", "сверь", "целостность файла"),
       examples=("файл=@homelab/homelab.json",), needs=())
def cksum(ctx: Context, text: str):
    raw = text.replace("файл=", "").replace("file=", "").strip().split()[0]
    p = resolve_path(ctx, raw)
    if not p.is_file():
        raise ToolError("нужен файл")
    data = p.read_bytes()
    return kv([("файл", p.name), ("размер", human_bytes(len(data))),
               ("sha256", hashlib.sha256(data).hexdigest())])


@agent("fs.archive", "Архив tar.gz", "files",
       "Упаковывает каталог в out/*.tar.gz (без секретов)",
       keywords=("архив", "tar", "сожми", "упакуй", "zip", "бэкап файлов"),
       examples=("path=@app/agentos/docs",), needs=("fs-write"), tags=("write",))
def archive(ctx: Context, text: str):
    params, rest = parse_kv(text)
    base = resolve_path(ctx, params.get("path") or rest or ".")
    if not base.is_dir():
        raise ToolError("нужен каталог")
    name = Path(params.get("name") or f"{base.name}.tar.gz").name
    if not name or name in (".", ".."):
        raise ValueError("плохое имя архива")
    target = resolve_path(ctx, f"out/{name}", write=True)
    if ctx.dry_run:
        return f"dry-run: {base} → {target} (--live)"
    ctx.out.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, "w:gz") as tar:
        for item in base.iterdir():
            if item.name in ("__pycache__", ".git"):
                continue
            tar.add(item, arcname=f"{base.name}/{item.name}")
    return f"архив: {target} ({human_bytes(target.stat().st_size)})"


@agent("fs.type", "Тип файла", "files",
       "Определяет тип по сигнатуре (PNG, JPEG, GIF, WebP, PDF, ZIP, ELF…)",
       keywords=("тип файла", "file", "сигнатура", "что за файл", "формат"),
       examples=("файл=@homelab/homelab.json",), needs=())
def ftype(ctx: Context, text: str):
    raw = text.replace("файл=", "").replace("file=", "").strip().split()[0]
    p = resolve_path(ctx, raw)
    with p.open("rb") as fh:
        head = fh.read(64)
    sigs = [
        (b"\x89PNG\r\n\x1a\n", "PNG image"), (b"\xff\xd8\xff", "JPEG image"),
        (b"GIF8", "GIF image"), (b"RIFF", "RIFF (WebP/WAV/AVI)"),
        (b"%PDF", "PDF document"), (b"PK\x03\x04", "ZIP archive"),
        (b"\x1f\x8b", "gzip"), (b"\x7fELF", "ELF executable"),
        (b"BZh", "bzip2"), (b"7z\xbc\xaf", "7-Zip"), (b"ID3", "MP3 with ID3"),
    ]
    kind = next((name for sig, name in sigs if head.startswith(sig)), None)
    if head.startswith((b"{", b"[")):
        kind = "JSON/текст"
    elif head.startswith(b"<"):
        kind = "XML/HTML"
    elif all(32 <= b < 127 or b in (9, 10, 13) for b in head[:32]):
        kind = "текст"
    return kv([("файл", p.name), ("тип", kind or "неизвестно"),
               ("сигнатура", head[:12].hex(" ")),
               ("размер", human_bytes(p.stat().st_size))])
