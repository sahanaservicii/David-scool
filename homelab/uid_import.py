#!/usr/bin/env python3
"""Сохранить UID пропуска, прочитанный ридером, в локальный файл.

Только stdlib, только локальные файлы. UID не печатается в выводе —
на экран идут только путь, длина и короткий отпечаток SHA-256.

Пример:
    python3 uid_import.py --from-file /root/workspace/kindergarten.uid.txt \
        --label kindergarten
"""

import argparse
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "state" / "cards"


def sanitize_label(label: str) -> str:
    clean = re.sub(r"[^a-z0-9_-]+", "-", label.lower()).strip("-")
    if not clean:
        raise SystemExit("ERROR: пустой label")
    return clean


def parse_uid(raw: str) -> str:
    line = next((s.strip() for s in raw.splitlines() if s.strip()), "")
    if not line:
        raise SystemExit("ERROR: файл пуст")
    uid = re.sub(r"[\s:,\-]", "", line).upper()
    if not re.fullmatch(r"[0-9A-F]{4,32}", uid):
        raise SystemExit("ERROR: ожидался HEX UID (4–32 символа)")
    return uid


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-file", required=True, help="файл с UID от ридера")
    ap.add_argument("--label", default="kindergarten", help="имя карты в имени файла")
    ap.add_argument("--force", action="store_true", help="перезаписать существующий файл")
    args = ap.parse_args()

    src = Path(args.from_file).expanduser()
    if not src.is_file():
        raise SystemExit(f"ERROR: нет файла {src}")

    uid = parse_uid(src.read_text(encoding="utf-8", errors="replace"))
    label = sanitize_label(args.label)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / f"{label}.uid.txt"
    if dest.exists() and not args.force:
        raise SystemExit(f"ERROR: {dest} уже есть; добавь --force для перезаписи")

    dest.write_text(uid + "\n", encoding="utf-8")
    digest = hashlib.sha256(uid.encode()).hexdigest()[:12]
    print(f"OK: {dest}")
    print(f"длина: {len(uid) // 2} байт, отпечаток: {digest}")
    print(f"время: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
