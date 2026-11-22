#!/usr/bin/env python3
"""Сборка переносимого офлайн-комплекта agentos (USB, Windows 10, Linux/Android).

    python3 tools/build_portable.py            # dist/agentos-portable/ + zip

В комплект входит Python 3.12 для Windows (embeddable, PSF license), поэтому
на Windows ничего ставить не нужно. Для Linux/Android используется системный
python3. Первый запуск сам создаёт data/, out/ и конфиг.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DIST = ROOT / "dist"
NAME = "agentos-portable"
VERSION = "1.0.0"

from agentos.core import EXPECTED_AGENTS  # noqa: E402

RUNTIME_VER = "3.12.10"
RUNTIME_ZIP = ROOT / "tools" / "cache" / f"python-{RUNTIME_VER}-embed-amd64.zip"
RUNTIME_SRC = f"https://www.python.org/ftp/python/{RUNTIME_VER}/python-{RUNTIME_VER}-embed-amd64.zip"

SKIP_DIRS = {"__pycache__", ".git", "state", "backups"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n in SKIP_DIRS or Path(n).suffix in SKIP_SUFFIXES}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_runtime(target: Path) -> bool:
    """Распаковывает Windows-Python и правит _pth, чтобы виден был корень."""
    if not RUNTIME_ZIP.exists():
        print(f"! нет {RUNTIME_ZIP} — Windows-комплект будет без Python")
        return False
    dest = target / "runtime" / "python-win64"
    dest.mkdir(parents=True)
    with zipfile.ZipFile(RUNTIME_ZIP) as zf:
        zf.extractall(dest)

    pth = next(dest.glob("python3*._pth"), None)
    if pth:
        lines = [ln for ln in pth.read_text("utf-8").splitlines() if ln.strip()]
        if "..\\.." not in lines:
            # корень комплекта относительно runtime\\python-win64
            pos = lines.index("#import site") if "#import site" in lines else len(lines)
            lines.insert(pos, "..\\..")
            pth.write_text("\n".join(lines) + "\n", "utf-8")

    (target / "runtime" / "README.txt").write_text(
        f"Python {RUNTIME_VER} for Windows (embeddable, 64-bit)\n"
        f"Источник: {RUNTIME_SRC}\n"
        f"sha256: {sha256(RUNTIME_ZIP)}\n"
        "Лицензия: PSF License (файл LICENSE.txt внутри python-win64).\n"
        "Ставить ничего не нужно: run.cmd использует этот интерпретатор.\n",
        "utf-8")
    return True


def build(zip_it: bool = True) -> Path:
    target = DIST / NAME
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    shutil.copytree(ROOT / "agentos", target / "agentos", ignore=ignore)
    shutil.copytree(ROOT / "tests", target / "tests", ignore=ignore)
    shutil.copytree(ROOT / "bin", target / "bin", ignore=ignore)

    homelab_src = ROOT.parent / "homelab"
    if homelab_src.exists():
        shutil.copytree(homelab_src, target / "homelab", ignore=ignore)

    for name in ("README.md", "RUNBOOK.md", "CATALOG.md"):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, target / name)

    has_runtime = ensure_runtime(target)

    # ---------- Linux / Android ----------
    (target / "run.sh").write_text(
        '#!/bin/sh\n'
        '# Переносимый запуск: нужен только python3 (3.10+).\n'
        'cd "$(dirname "$0")" || exit 1\n'
        'command -v python3 >/dev/null 2>&1 || { echo "нужен python3 3.10+"; exit 1; }\n'
        'exec python3 -m agentos "$@"\n', "utf-8")
    (target / "start.sh").write_text(
        '#!/bin/sh\n'
        '# Двойной клик/запуск: браузерный интерфейс на 127.0.0.1\n'
        'cd "$(dirname "$0")" || exit 1\n'
        'exec sh ./run.sh serve --open "$@"\n', "utf-8")
    (target / "start-lan.sh").write_text(
        '#!/bin/sh\n'
        '# Доступ с телефона/другого ПК в той же LAN (токен обязателен)\n'
        'cd "$(dirname "$0")" || exit 1\n'
        'exec sh ./run.sh serve --host 0.0.0.0 --open "$@"\n', "utf-8")

    # ---------- Windows ----------
    python_cmd = ('if exist "runtime\\python-win64\\python.exe" (\r\n'
                  '  "runtime\\python-win64\\python.exe" -m agentos %*\r\n'
                  ') else (\r\n'
                  '  where py >nul 2>nul\r\n'
                  '  if errorlevel 1 (\r\n'
                  '    python -m agentos %*\r\n'
                  '  ) else (\r\n'
                  '    py -3 -m agentos %*\r\n'
                  '  )\r\n'
                  ')\r\n')
    (target / "run.cmd").write_text(
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "cd /d \"%~dp0\"\r\n"
        "set PYTHONUTF8=1\r\n"
        "set PYTHONIOENCODING=utf-8\r\n"
        + python_cmd, "utf-8")

    (target / "start.cmd").write_text(
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "call run.cmd serve --open %*\r\n", "utf-8")

    (target / "start-lan.cmd").write_text(
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "call run.cmd serve --host 0.0.0.0 --open %*\r\n", "utf-8")

    (target / "bin" / "agentos.cmd").write_text(
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "cd /d \"%~dp0..\"\r\n"
        + python_cmd, "utf-8")

    if os.name != "nt":                      # на Windows chmod бессмысленен
        for script in ("run.sh", "start.sh", "start-lan.sh", "bin/agentos"):
            (target / script).chmod(0o755)

    (target / "PORTABLE.md").write_text(PORTABLE_DOC, "utf-8")
    (target / "MANIFEST.txt").write_text(
        f"agentos portable {VERSION}\n"
        f"агентов: {EXPECTED_AGENTS}, категорий: 11\n"
        f"зависимости: python3 (stdlib), на Windows встроен Python {RUNTIME_VER}\n"
        f"windows runtime: {'да' if has_runtime else 'нет'}\n"
        f"windows runtime sha256: {sha256(RUNTIME_ZIP) if has_runtime else '-'}\n",
        "utf-8")

    if zip_it:
        archive = shutil.make_archive(str(DIST / f"{NAME}-{VERSION}"), "zip",
                                      root_dir=str(DIST), base_dir=NAME)
        size = Path(archive).stat().st_size
        print(f"архив: {archive} ({size // (1024 * 1024)} МБ)")
    total = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    print(f"каталог: {target} ({total // (1024 * 1024)} МБ)")
    return target


PORTABLE_DOC = r"""# agentos portable — офлайн, с флешки, браузерный интерфейс

## Windows 10 (ничего ставить не нужно)

1. Распаковать zip **полностью** (не запускать из окна архива).
2. Двойной клик `start.cmd` — откроется браузер с интерфейсом.
   Внутри уже лежит Python 3.12, pip и интернет не нужны.
3. `start-lan.cmd` — то же, но доступно с телефона/другого ПК в той же сети
   (токен печатается в консоли и подставляется в ссылку).

Проверка без сервера:

```bat
run.cmd selftest
run.cmd "посчитай 2+2*10"
```

## Linux / macOS

```bash
./run.sh selftest
./start.sh            # браузер на 127.0.0.1
./start-lan.sh        # доступ из LAN
```

Нужен системный `python3` 3.10+ (обычно уже есть).

## Android (Termux)

```bash
pkg install python
cd ~/agentos-portable
./run.sh selftest
./start-lan.sh        # затем открыть ссылку в браузере телефона
```

## Как устроен браузерный доступ

- `/` — мобильная страница: запрос, выбор агента, подсказки, история.
- `/health` — статус без токена; `/agents` и `/ask` — по токену.
- Токен хранится в `data/config.json`; при первом старте генерируется.
- По умолчанию сервер слушает `127.0.0.1`; `--host 0.0.0.0` открывает
  доступ только в локальной сети. Наружу порт не пробрасывать.
- `--live` разрешает изменяющие действия; без него всё в dry-run.

## Что внутри

- `agentos/` — 113 агентов (включая Windows: cmd, PowerShell, службы), ядро, роутер, память (SQLite);
- `homelab/` — сетевые/HA/ADB-инструменты;
- `runtime/python-win64/` — Python 3.12 для Windows (PSF license);
- `tests/` — 52 теста;
- `data/` и `out/` создаются при первом запуске, рядом с комплектом
  (на read-only носителе — в `%LOCALAPPDATA%` или `~/.local/share/agentos`).

## Ограничения

- Нет `ip`/`ping`/`ss` на минимальных системах — агенты честно сообщают;
  ARP берётся из `homelab.py inventory`, доступность проверяется по TCP.
- ADB-агенты требуют `adb` и включённую отладку; ADB в комплект не входит.
- Секреты не входят: положите в `~/.config/opencode/secrets/homelab.env`.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="собрать переносимый agentos")
    ap.add_argument("--no-zip", action="store_true", help="без zip-архива")
    args = ap.parse_args(argv)
    target = build(zip_it=not args.no_zip)
    return 0 if target.exists() else 1


if __name__ == "__main__":
    sys.exit(main())
