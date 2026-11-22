"""Агенты-обёртки над homelab.py: отчёты, бэкапы, уведомления, состояние."""
from __future__ import annotations

import json
import stat
from pathlib import Path

from ..core import HOMELAB_DIR, Context, agent
from ..tools import homelab, ToolError
from ..utils import kv, table, truncate

SECRETS = Path.home() / ".config/opencode/secrets/homelab.env"


@agent("hl.report", "Отчёт по сети", "homelab",
       "Собирает Markdown-отчёт о домашней сети через homelab.py report",
       keywords=("отчёт", "report", "сводка", "состояние сети", "документ"),
       examples=("",), needs=("homelab",), tags=("write",))
def report(ctx: Context, text: str):
    if ctx.dry_run:
        return "dry-run: homelab.py report → reports/*.md (рядом с приложением, запуск с --live)"
    r = homelab(ctx, ["report"], timeout=180)
    return (r["out"] or r["err"])[:6000]


@agent("hl.backup", "Бэкап", "homelab",
       "Бэкап конфигов роутера и Home Assistant в homelab/backups",
       keywords=("бэкап", "backup", "резервная копия", "сохрани конфиг", "архив"),
       examples=("router",), needs=("homelab",), tags=("write", "slow"))
def backup(ctx: Context, text: str):
    args = ["backup"]
    if "router" in (text or "") or "роутер" in (text or "").lower() or not text.strip():
        args.append("--with-router")
    if "ha" in (text or "").lower() or "home" in (text or "").lower():
        args.append("--with-ha")
    if ctx.dry_run:
        return f"dry-run: homelab.py {' '.join(args)} (запуск с --live)"
    r = homelab(ctx, args, timeout=300)
    return (r["out"] or r["err"])[:6000]


@agent("hl.notify", "Уведомление", "homelab",
       "Отправляет уведомление на телефон через локальный мост",
       keywords=("уведомление", "notify", "напиши на телефон", "сообщи", "пуш"),
       examples=("Проверка связи",), needs=("homelab",), tags=("write",))
def notify(ctx: Context, text: str):
    msg = (text or "").strip() or "Домовой на связи"
    if ctx.dry_run:
        return f"dry-run: уведомление «{msg}» (запуск с --live)"
    r = homelab(ctx, ["notify", "--message", msg], timeout=60)
    return (r["out"] or r["err"] or "отправлено")[:2000]


@agent("hl.state", "Состояние", "homelab",
       "Содержимое state/: последние сканы, бэкапы и служебные файлы",
       keywords=("состояние", "state", "файлы состояния", "последний скан", "данные"),
       examples=("",), needs=("homelab",))
def state(ctx: Context, text: str):
    sdir = HOMELAB_DIR / "state"
    if not sdir.exists():
        return "каталог state/ отсутствует"
    rows = []
    for p in sorted(sdir.iterdir()):
        if p.is_file():
            st = p.stat()
            extra = ""
            if p.suffix == ".json":
                try:
                    obj = json.loads(p.read_text("utf-8"))
                    if isinstance(obj, dict):
                        extra = f"{len(obj)} ключей"
                    elif isinstance(obj, list):
                        extra = f"{len(obj)} записей"
                except ValueError:
                    extra = "битый json"
            rows.append([p.name, f"{st.st_size} Б", extra])
    if not rows:
        return "state/ пуст"
    return table(rows, ["файл", "размер", "содержимое"])


@agent("hl.diff", "Инвентарь vs скан", "homelab",
       "Сравнивает последний скан с инвентарём: новые и пропавшие устройства",
       keywords=("сравни", "новые устройства", "пропали", "изменения", "diff"),
       examples=("",), needs=("homelab",))
def diff(ctx: Context, text: str):
    inv_path = HOMELAB_DIR / "homelab.json"
    scan_path = HOMELAB_DIR / "state" / "scan.json"
    if not inv_path.exists():
        raise ToolError("нет homelab.json")
    inv = json.loads(inv_path.read_text("utf-8"))
    known = set()
    for key in ("router", "home_assistant"):
        if isinstance(inv.get(key), dict) and inv[key].get("host"):
            known.add(inv[key]["host"])
    for key in ("android", "cameras"):
        for dev in inv.get(key, []) or []:
            if dev.get("host"):
                known.add(dev["host"])
    if not scan_path.exists():
        return (f"инвентарь: {len(known)} устройств; скан ещё не делался "
                f"(запусти net.scan с --live)")
    scan = json.loads(scan_path.read_text("utf-8"))
    hosts = set()
    items = scan if isinstance(scan, list) else scan.get("hosts", scan)
    if isinstance(items, dict):
        items = list(items.values())
    for it in items or []:
        if isinstance(it, dict):
            h = it.get("ip") or it.get("host")
            if h:
                hosts.add(h)
        elif isinstance(it, str):
            hosts.add(it)
    new = sorted(hosts - known)
    gone = sorted(known - hosts)
    out = [f"инвентарь: {len(known)}, в скане: {len(hosts)}"]
    out.append("новые: " + (", ".join(new) if new else "нет"))
    out.append("нет в скане: " + (", ".join(gone) if gone else "нет"))
    return "\n".join(out)


@agent("hl.secrets", "Аудит секретов", "homelab",
       "Проверяет наличие и права файла секретов, не показывая содержимое",
       keywords=("секреты", "secrets", "токен", "права доступа", "безопасность файла"),
       examples=("",), needs=("homelab",), secret=True)
def secrets(ctx: Context, text: str):
    if not SECRETS.exists():
        return ("файл секретов не найден\n"
                f"создай: {SECRETS} (chmod 600) — см. homelab/README.md")
    st = SECRETS.stat()
    mode = stat.S_IMODE(st.st_mode)
    keys = []
    for line in SECRETS.read_text("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.append(line.split("=", 1)[0])
    warn = "OK" if mode & 0o077 == 0 else "!! доступ группе/другим"
    return kv([("путь", SECRETS), ("права", f"{mode:o} ({warn})"),
               ("ключей", len(keys)), ("имена", ", ".join(keys) or "-")])


@agent("hl.changelog", "Запись в changelog", "homelab",
       "Добавляет строку в homelab/CHANGELOG.md (дата + текст)",
       keywords=("changelog", "журнал", "запиши изменение", "история"),
       examples=("Проверка системы агентов",), needs=("homelab",), tags=("write",))
def changelog(ctx: Context, text: str):
    from datetime import datetime
    entry = (text or "").strip()
    if not entry:
        raise ValueError("что записать?")
    path = HOMELAB_DIR / "CHANGELOG.md"
    line = f"- {datetime.now().strftime('%Y-%m-%d %H:%M')} — {entry}\n"
    if ctx.dry_run:
        return f"dry-run: дописать в {path}:\n{line.strip()}"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return f"записано в CHANGELOG.md: {entry}"


@agent("hl.plan", "План обслуживания", "homelab",
       "Строит план работ по инвентарю: что проверить, обновить, забэкапить",
       keywords=("план", "обслуживание", "что делать", "чеклист", "порядок работ"),
       examples=("",), needs=("homelab",))
def plan(ctx: Context, text: str):
    inv_path = HOMELAB_DIR / "homelab.json"
    inv = json.loads(inv_path.read_text("utf-8")) if inv_path.exists() else {}
    steps = []
    scan = HOMELAB_DIR / "state" / "scan.json"
    if not scan.exists():
        steps.append("1. Сделать первичный скан: net.scan --live")
    steps.append("2. Проверить доступность: net.doctor")
    if not SECRETS.exists():
        steps.append("3. Создать файл секретов 600 (HASS_TOKEN, HOMELAB_SSH_KEY)")
    else:
        steps.append("3. Секреты на месте — проверить права: hl.secrets")
    if inv.get("cameras"):
        steps.append(f"4. Аудит камер ({len(inv['cameras'])} шт): sec.cameras")
    if any(a.get("port") == 5555 for a in inv.get("android", []) or []):
        steps.append("5. ADB 5555 держать выключенным вне работ: sec.exposure")
    steps.append("6. Бэкап роутера и HA: hl.backup \"router ha\" --live")
    steps.append("7. Отчёт и changelog: hl.report, hl.changelog")
    return "План обслуживания:\n" + "\n".join(steps)
