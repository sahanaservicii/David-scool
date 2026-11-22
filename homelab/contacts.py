#!/usr/bin/env python3
"""Офлайн-работа с контактами (vCard): слияние, дедупликация, разбор по группам.

Только stdlib. Никакой сети и облака: на вход .vcf, на выход .vcf.

Примеры:
    python3 contacts.py stats a.vcf b.vcf
    python3 contacts.py merge -o merged.vcf a.vcf b.vcf
    python3 contacts.py split merged.vcf -o out/          # по первой букве имени
"""

import argparse
import os
import re
import sys
import unicodedata

PHONE_KEEP = {"TEL", "EMAIL", "NOTE", "ORG", "TITLE", "BDAY", "ADR", "URL"}


def unfold(text):
    """vCard line folding (RFC 6350): строки, начинающиеся с пробела/таба — продолжение."""
    out = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and out:
            out[-1] += raw[1:]
        else:
            out.append(raw)
    return out


def parse_cards(text):
    cards, cur = [], []
    for line in unfold(text):
        up = line.strip().upper()
        if up == "BEGIN:VCARD":
            cur = ["BEGIN:VCARD"]
        elif up == "END:VCARD":
            cur.append("END:VCARD")
            if len(cur) > 2:
                cards.append(cur)
            cur = []
        elif cur:
            cur.append(line)
    return cards


def get_prop(card, name):
    vals = []
    for line in card:
        head = line.split(":", 1)[0].upper()
        base = head.split(";", 1)[0]
        if base == name:
            vals.append(line.split(":", 1)[1] if ":" in line else "")
    return vals


def norm_phone(value):
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    return digits


def display_name(card):
    fn = get_prop(card, "FN")
    if fn:
        return fn[0].strip()
    n = get_prop(card, "N")
    if n:
        parts = [p for p in n[0].split(";") if p.strip()]
        return " ".join(reversed(parts)).strip()
    return ""


def card_keys(card):
    """Ключи для сравнения: нормализованные телефоны и e-mail."""
    keys = set()
    for tel in get_prop(card, "TEL"):
        d = norm_phone(tel)
        if len(d) >= 9:
            keys.add("T:" + d[-10:])
    for mail in get_prop(card, "EMAIL"):
        m = mail.strip().lower()
        if "@" in m:
            keys.add("E:" + m)
    return keys


def merge_cards(cards):
    """Слить карточки: одинаковые ключи (телефон/e-mail) — одна карточка."""
    merged, index = [], {}
    for card in cards:
        keys = card_keys(card)
        target = None
        for k in keys:
            if k in index:
                target = index[k]
                break
        if target is None:
            target = {"cards": [], "lines": [], "keys": set()}
            merged.append(target)
        target["cards"].append(card)
        target["keys"] |= keys
        for k in target["keys"]:
            index[k] = target

    result = []
    for group in merged:
        base = list(group["cards"][0])
        seen_lines = {
            line.split(":", 1)[0].upper() + "|" + line.split(":", 1)[-1].strip().lower()
            for line in base
        }
        for extra in group["cards"][1:]:
            for line in extra:
                base_name = line.split(":", 1)[0].split(";", 1)[0].upper()
                sign = line.split(":", 1)[0].upper() + "|" + line.split(":", 1)[-1].strip().lower()
                if base_name in ("BEGIN", "END", "VERSION", "PRODID", "REV", "UID"):
                    continue
                if base_name in PHONE_KEEP and sign not in seen_lines:
                    insert_at = len(base) - 1
                    base.insert(insert_at, line)
                    seen_lines.add(sign)
        result.append(base)
    return result


def write_vcf(cards, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        for card in cards:
            fh.write("\r\n".join(card) + "\r\n")
    return path


def read_vcf(paths):
    cards = []
    for path in paths:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            cards.extend(parse_cards(fh.read()))
    return cards


def bucket(name):
    letter = unicodedata.normalize("NFKD", (name or "#").strip()[:1]).upper()
    if not letter:
        return "#"
    if letter.isascii() and letter.isalpha():
        return letter
    table = {"А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "E",
             "Ж": "ZH", "З": "Z", "И": "I", "Й": "I", "К": "K", "Л": "L", "М": "M",
             "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U",
             "Ф": "F", "Х": "H", "Ц": "C", "Ч": "CH", "Ш": "SH", "Щ": "SCH",
             "Ъ": "#", "Ы": "Y", "Ь": "#", "Э": "E", "Ю": "YU", "Я": "YA"}
    return table.get(letter, "#")


def cmd_stats(args):
    cards = read_vcf(args.files)
    phones = sum(1 for c in cards for _ in get_prop(c, "TEL"))
    mails = sum(1 for c in cards for _ in get_prop(c, "EMAIL"))
    print(f"карточек: {len(cards)}  телефонов: {phones}  e-mail: {mails}")
    uniq = merge_cards(cards)
    print(f"после склейки дублей: {len(uniq)}")
    if args.files:
        for path in args.files:
            own = read_vcf([path])
            print(f"  {path}: {len(own)} карточек")
    return 0


def cmd_merge(args):
    cards = read_vcf(args.files)
    if not cards:
        print("нет карточек на входе", file=sys.stderr)
        return 1
    merged = merge_cards(cards)
    write_vcf(merged, args.output)
    print(f"вход: {len(cards)} карточек из {len(args.files)} файлов")
    print(f"выход: {len(merged)} карточек -> {args.output}")
    dropped = len(cards) - len(merged)
    if dropped:
        print(f"склеено дублей: {dropped}")
    return 0


def cmd_split(args):
    cards = read_vcf([args.file])
    groups = {}
    for card in cards:
        groups.setdefault(bucket(display_name(card)), []).append(card)
    for letter, items in sorted(groups.items()):
        path = os.path.join(args.output, f"{letter}.vcf")
        write_vcf(items, path)
    print(f"{len(cards)} карточек -> {len(groups)} файлов в {args.output}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="vCard: слияние и дедупликация (офлайн)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stats", help="сколько карточек и дублей")
    s.add_argument("files", nargs="+")
    s.set_defaults(func=cmd_stats)

    m = sub.add_parser("merge", help="слить в один .vcf без дублей")
    m.add_argument("-o", "--output", default="merged.vcf")
    m.add_argument("files", nargs="+")
    m.set_defaults(func=cmd_merge)

    sp = sub.add_parser("split", help="разложить по файлам A.vcf, B.vcf, ...")
    sp.add_argument("file")
    sp.add_argument("-o", "--output", default="contacts-out")
    sp.set_defaults(func=cmd_split)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
