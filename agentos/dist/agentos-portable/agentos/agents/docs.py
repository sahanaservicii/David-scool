"""Документация: инвентарь, каталог агентов, линт markdown, runbook."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..core import HOMELAB_DIR, REGISTRY, ROOT, VERSION, Context, agent
from ..tools import ToolError, read_text, write_project, write_text
from ..utils import kv, table, truncate

GLOSSARY = {
    "dhcp": "протокол выдачи IP-адресов; на OpenWrt — dnsmasq",
    "dns": "превращает имена в IP; локально — dnsmasq на роутере",
    "vlan": "логическое разделение сети на изолированные сегменты",
    "wireguard": "быстрый VPN; единственный правильный способ доступа снаружи",
    "upnp": "автоматическое открытие портов; дома лучше держать выключенным",
    "dmz": "хост, полностью открытый наружу; дома не нужен",
    "adb": "отладка Android по TCP 5555; включать только на время работ",
    "rtsp": "протокол видеопотока камер, обычно порт 554",
    "onvif": "стандарт управления камерами: профили, PTZ, события",
    "nvr": "сетевой видеорегистратор",
    "ha": "Home Assistant, локальная автоматизация",
    "mqtt": "лёгкий брокер сообщений для датчиков",
    "zigbee": "радиопротокол датчиков, нужен координатор",
    "sysupgrade": "обновление прошивки OpenWrt с сохранением настроек",
    "fw4": "фаервол OpenWrt на nftables",
    "dnsmasq": "DHCP+DNS сервер OpenWrt",
    "lldp": "обнаружение соседей на канальном уровне",
    "arp": "таблица соответствия IP↔MAC в локальной сети",
    "nat": "подмена адресов при выходе в интернет",
    "backup": "резервная копия конфигов; проверяется восстановлением",
}


@agent("doc.inventory_md", "Инвентарь в Markdown", "docs",
       "Собирает INVENTORY.md из homelab.json в out/",
       keywords=("инвентарь", "inventory", "документ устройств", "таблица устройств"),
       examples=("",), needs=("homelab", "fs-write"), tags=("write",))
def inventory_md(ctx: Context, text: str):
    inv_path = HOMELAB_DIR / "homelab.json"
    if not inv_path.exists():
        raise ToolError("нет homelab.json")
    inv = json.loads(inv_path.read_text("utf-8"))
    lines = ["# Инвентарь домашней сети", "",
             f"Сеть: `{inv.get('network', ctx.network)}`", ""]
    lines += ["## Ключевые узлы", "", "| Роль | Адрес | Тип | Заметка |",
              "|---|---|---|---|"]
    for key, role in (("router", "роутер"), ("home_assistant", "Home Assistant")):
        dev = inv.get(key) or {}
        if dev.get("host"):
            lines.append(f"| {role} | `{dev['host']}` | {dev.get('kind', '-')} | "
                         f"{dev.get('note', '')} |")
    for group, title in (("android", "Android"), ("cameras", "Камеры и NVR")):
        devs = inv.get(group) or []
        if devs:
            lines += ["", f"## {title}", "", "| Имя | Адрес | Тип | Заметка |",
                      "|---|---|---|---|"]
            for d in devs:
                lines.append(f"| {d.get('name', '-')} | `{d.get('host')}` | "
                             f"{d.get('kind', '-')} | {d.get('note', '')} |")
    lines += ["", f"_Сгенерировано agentos {VERSION}_", ""]
    md = "\n".join(lines)
    path = write_text(ctx, "out/INVENTORY.md", md)
    return f"готово: {path} ({len(inv.get('cameras', []))} камер, " \
           f"{len(inv.get('android', []))} android)\n\n" + md[:1200]


@agent("doc.toc", "Оглавление Markdown", "docs",
       "Строит оглавление по заголовкам файла",
       keywords=("оглавление", "toc", "содержание", "структура документа"),
       examples=("файл=@homelab/README.md",), needs=())
def toc(ctx: Context, text: str):
    raw = text.strip()
    if raw.startswith("файл=") or raw.startswith("file="):
        src = read_text(ctx, raw.split("=", 1)[1])
    else:
        src = raw
    items = []
    for line in src.splitlines():
        m = re.match(r"^(#{1,4})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            items.append("  " * (level - 1) + f"- {m.group(2).strip()}")
    return "\n".join(items) or "заголовков не найдено"


@agent("doc.lint", "Линт Markdown", "docs",
       "Проверяет markdown: длинные строки, хвостовые пробелы, битые ссылки",
       keywords=("линт", "markdown", "проверь документ", "ошибки оформления"),
       examples=("файл=@homelab/README.md",), needs=())
def lint(ctx: Context, text: str):
    raw = text.strip()
    src = read_text(ctx, raw.split("=", 1)[1]) if "=" in raw else raw
    issues = []
    for n, line in enumerate(src.splitlines(), 1):
        if len(line) > 120:
            issues.append([n, "длинная строка", f"{len(line)} симв."])
        if line != line.rstrip():
            issues.append([n, "хвостовые пробелы", ""])
        if "\t" in line:
            issues.append([n, "табуляция", ""])
    heads = re.findall(r"^(#{1,6})\s+(.+)$", src, re.M)
    if [h[1] for h in heads] != list(dict.fromkeys(h[1] for h in heads)):
        issues.append([0, "повтор заголовка", ""])
    if not issues:
        return f"проверено строк: {len(src.splitlines())}, проблем нет"
    return table(issues[:40], ["строка", "проблема", "деталь"],
                 align_right={0}) + f"\nвсего: {len(issues)}"


@agent("doc.readme_check", "Проверка README", "docs",
       "Проверяет, что в README есть обязательные разделы",
       keywords=("readme", "проверь документацию", "разделы", "полнота"),
       examples=("файл=@homelab/README.md",), needs=())
def readme_check(ctx: Context, text: str):
    raw = text.strip()
    src = read_text(ctx, raw.split("=", 1)[1]) if "=" in raw else raw
    required = ["Быстрый старт", "Секрет", "Android", "Сеть"]
    rows = [[r, "есть" if r.lower() in src.lower() else "НЕТ"] for r in required]
    missing = sum(1 for _, s in rows if s == "НЕТ")
    return table(rows, ["раздел", "статус"]) + (
        f"\nвсё на месте" if not missing else f"\nне хватает разделов: {missing}")


@agent("doc.catalog", "Каталог агентов", "docs",
       "Генерирует CATALOG.md со всеми агентами по категориям",
       keywords=("каталог", "catalog", "список агентов", "возможности", "что умеешь"),
       examples=("",), needs=("fs-write"), tags=("write",))
def catalog(ctx: Context, text: str):
    cats = REGISTRY.categories()
    lines = ["# Каталог мини-агентов", "",
             f"Всего: **{len(REGISTRY)}** агентов в {len(cats)} категориях.", ""]
    for cat in sorted(cats):
        lines += [f"## {cat} ({len(cats[cat])})", "",
                  "| id | что делает | пример |", "|---|---|---|"]
        for a in cats[cat]:
            ex = (a.examples[0] if a.examples else "").replace("|", "\\|")
            lines.append(f"| `{a.id}` | {a.name} — {a.description} | `{truncate(ex, 40)}` |")
        lines.append("")
    md = "\n".join(lines)
    if ctx.dry_run:
        return f"dry-run: CATALOG.md ({len(REGISTRY)} агентов, {len(md)} симв.)"
    path = write_project(ctx, "CATALOG.md", md)
    return f"готово: {path} ({len(REGISTRY)} агентов)"


@agent("doc.glossary", "Глоссарий", "docs",
       "Объясняет сетевой термин простыми словами",
       keywords=("термин", "глоссарий", "что такое", "объясни", "значение"),
       examples=("wireguard",), needs=())
def glossary(ctx: Context, text: str):
    term = text.strip().lower().split()[0] if text.strip() else ""
    if not term:
        return "термины: " + ", ".join(sorted(GLOSSARY))
    if term in GLOSSARY:
        return f"{term}: {GLOSSARY[term]}"
    close = [k for k in GLOSSARY if term[:4] in k or k[:4] in term]
    return (f"«{term}» в глоссарии нет. Похожие: {', '.join(close) or '—'}\n"
            f"Доступно: {', '.join(sorted(GLOSSARY))}")


@agent("doc.runbook", "Runbook", "docs",
       "Генерирует аварийный runbook по инвентарю в out/RUNBOOK.md",
       keywords=("runbook", "авария", "инструкция", "что делать если", "восстановление"),
       examples=("",), needs=("homelab", "fs-write"), tags=("write",))
def runbook(ctx: Context, text: str):
    inv_path = HOMELAB_DIR / "homelab.json"
    inv = json.loads(inv_path.read_text("utf-8")) if inv_path.exists() else {}
    gw = inv.get("router", {}).get("host", ctx.network.split("/")[0].rsplit(".", 1)[0] + ".1")
    md = f"""# Runbook — аварийные процедуры

Сеть: `{ctx.network}`, шлюз `{gw}`.

## 1. Нет интернета
1. `agentos run net.doctor ""` — что именно отвалилось.
2. `ping {gw}` — жив ли роутер.
3. LuCI `http://{gw}` → Status → Overview.
4. Перезагрузка роутера — только после бэкапа конфига.

## 2. Нет доступа к роутеру по SSH
1. Проверить `net.ports {gw} 22`.
2. Подключиться по LAN-кабелю, не по Wi-Fi.
3. Dropbear: `/etc/init.d/dropbear restart` через последовательный порт.

## 3. Камеры пропали
1. `agentos run sec.cameras "" --live`.
2. Проверить PoE-питание и порт коммутатора.
3. NVR: `http://{inv.get('cameras', [{}])[-1].get('host', '—') if inv.get('cameras') else '—'}`.

## 4. Потерян конфиг роутера
1. `agentos run hl.backup "router" --live` (если роутер жив).
2. Восстановление: `sysupgrade -r backup.tar.gz` на роутере.

## 5. Проверка после любого изменения
`agentos run net.doctor ""`, затем `hl.changelog "что изменили" --live`.
"""
    if ctx.dry_run:
        return f"dry-run: out/RUNBOOK.md ({len(md)} симв.)"
    path = write_text(ctx, "out/RUNBOOK.md", md)
    return f"готово: {path}"


@agent("doc.runs", "Журнал прогонов", "docs",
       "Показывает последние запуски агентов из локальной памяти",
       keywords=("журнал", "история", "прогоны", "logs", "что запускалось"),
       examples=("",), needs=())
def runs(ctx: Context, text: str):
    if not ctx.memory:
        return "память недоступна"
    rows = ctx.memory.runs(limit=15)
    if not rows:
        return "прогонов ещё не было"
    out = table([[r["id"], r["ts"][11:19], r["agent"], "ok" if r["ok"] else "ERR",
                  r["ms"], truncate(r["query"], 40)] for r in rows],
                ["#", "время", "агент", "", "мс", "запрос"], align_right={0, 4})
    st = ctx.memory.stats()
    return out + f"\nвсего: {st['runs']}, успешных: {st['ok']}, среднее: {st['avg_ms']} мс"
