"""Мини-агенты безопасности: аудит своей сети, без подбора паролей."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import string
from pathlib import Path

from ..core import HOMELAB_DIR, ROOT, Context, agent
from ..tools import (ToolError, http_fetch, is_local_host, resolve_path,
                     run_cmd, tcp_check)
from ..utils import kv, table, human_bytes

RISKY_PORTS = {
    23: "telnet — открытый текст",
    21: "ftp — открытый текст",
    5555: "adb — удалённое управление",
    7547: "TR-069 — частая дыра роутеров",
    2323: "telnet-альтернатива",
    9527: "часто у NVR/XM",
    34567: "XM DVR",
}


@agent("sec.ports", "Аудит портов", "security",
       "Проверяет у известных устройств опасные порты из локального списка",
       keywords=("аудит портов", "опасные порты", "что открыто", "сканируй устройства"),
       examples=("",), needs=("net", "homelab"), tags=("slow",))
def ports(ctx: Context, text: str):
    inv_path = HOMELAB_DIR / "homelab.json"
    if not inv_path.exists():
        return "нет homelab.json — нечего проверять"
    inv = json.loads(inv_path.read_text("utf-8"))
    hosts = []
    for key in ("router", "home_assistant"):
        if isinstance(inv.get(key), dict) and inv[key].get("host"):
            hosts.append(inv[key]["host"])
    for key in ("android", "cameras"):
        for dev in inv.get(key, []) or []:
            if dev.get("host"):
                hosts.append(dev["host"])
    hosts = list(dict.fromkeys(hosts))[:14]
    if ctx.dry_run:
        return ("dry-run: проверка " + ", ".join(hosts) +
                " по портам " + ", ".join(map(str, RISKY_PORTS)) + " (--live)")
    rows, findings = [], 0
    for host in hosts:
        for port, why in RISKY_PORTS.items():
            if tcp_check(host, port, timeout=0.6)["open"]:
                rows.append([host, port, why])
                findings += 1
    if not rows:
        return f"проверено {len(hosts)} устройств: опасных портов не открыто"
    return (f"найдено {findings} открытых опасных портов:\n"
            + table(rows, ["host", "порт", "почему плохо"], align_right={1}))


@agent("sec.exposure", "Слушающие сокеты", "security",
       "Какие порты слушает сам хост и не торчат ли они наружу (0.0.0.0)",
       keywords=("сокеты", "слушает", "наружу", "bind", "0.0.0.0", "открытые порты хоста"),
       examples=("",), needs=("net",))
def exposure(ctx: Context, text: str):
    r = run_cmd(ctx, ["ss", "-lntu"], timeout=5)
    if not r["ok"]:
        return f"ss недоступен: {r['err']}"
    rows, risky = [], []
    for line in r["out"].splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        proto, local = parts[0], parts[4]
        addr, _, port = local.rpartition(":")
        if port.isdigit() and int(port) > 0:
            flags = []
            if addr in ("0.0.0.0", "*", "[::]") and int(port) in RISKY_PORTS:
                flags.append("НАРУЖУ+риск")
                risky.append(int(port))
            elif int(port) in RISKY_PORTS:
                flags.append("риск")
            rows.append([proto, local, ",".join(flags) or ""])
    if not rows:
        return "не удалось разобрать ss"
    head = f"слушающих сокетов: {len(rows)}"
    if risky:
        head += "\n!! опасные порты на всех интерфейсах: " + ", ".join(
            str(p) for p in sorted(set(risky)))
    return head + "\n" + table(rows[:40], ["прото", "адрес", "замечание"])


@agent("sec.cameras", "Аудит камер", "security",
       "Проверяет камеры/NVR из инвентаря: доступные порты и веб-интерфейс",
       keywords=("камеры", "nvr", "видеонаблюдение", "rtsp", "аудит камер", "xm"),
       examples=("",), needs=("net", "homelab"), tags=("slow",))
def cameras(ctx: Context, text: str):
    inv_path = HOMELAB_DIR / "homelab.json"
    if not inv_path.exists():
        return "нет homelab.json"
    inv = json.loads(inv_path.read_text("utf-8"))
    cams = [c for c in (inv.get("cameras") or []) if c.get("host")][:12]
    if not cams:
        return "камер в инвентаре нет"
    if ctx.dry_run:
        return "dry-run: проверка " + ", ".join(c["host"] for c in cams) + " (--live)"
    rows = []
    for cam in cams:
        host = cam["host"]
        open_ports = [p for p in (80, 554, 8000, 34567, 9527)
                      if tcp_check(host, p, timeout=0.6)["open"]]
        web = ""
        if 80 in open_ports or 8000 in open_ports:
            r = http_fetch(ctx, f"http://{host}:{80 if 80 in open_ports else 8000}/",
                           method="GET", timeout=3, max_bytes=4000)
            web = f"HTTP {r.get('status') or '—'}"
        rows.append([cam.get("name", host), host, ",".join(map(str, open_ports)) or "—", web])
    warn = ("\n\nРекомендация: камеры — в отдельный VLAN/SSID без выхода в интернет, "
            "UPnP/P2P выключить, пароли сменить с заводских.")
    return table(rows, ["имя", "ip", "порты", "веб"]) + warn


@agent("sec.perms", "Права файлов", "security",
       "Ищет файлы, доступные на запись всем (0777/0666), в workspace",
       keywords=("права", "chmod", "0777", "доступ", "разрешения", "файлы"),
       examples=("",), needs=("net",))
def perms(ctx: Context, text: str):
    limit = 4000
    bad, seen = [], 0
    for base in (ROOT, HOMELAB_DIR):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in
                           ("__pycache__", ".git", "node_modules", "data")]
            for name in filenames:
                seen += 1
                if seen > limit:
                    break
                p = Path(dirpath) / name
                try:
                    mode = stat.S_IMODE(p.lstat().st_mode)
                except OSError:
                    continue
                if mode & 0o002:
                    bad.append([str(p.relative_to(ROOT.parent)), f"{mode:o}"])
    if not bad:
        return f"проверено файлов: {seen}, world-writable не найдено"
    return table(bad[:50], ["файл", "права"]) + f"\nвсего: {len(bad)}"


@agent("sec.passcheck", "Стойкость пароля", "security",
       "Оценивает длину и энтропию пароля, не сохраняя и не повторяя его",
       keywords=("пароль", "password", "стойкость", "энтропия", "надёжность"),
       examples=("Correct-Horse-42",), needs=(), secret=True)
def passcheck(ctx: Context, text: str):
    pwd = text.strip()
    if not pwd:
        raise ValueError("передай пароль после команды")
    pools = 0
    for chars, size in ((string.ascii_lowercase, 26), (string.ascii_uppercase, 26),
                        (string.digits, 10), (string.punctuation, 32)):
        if any(c in chars for c in pwd):
            pools += size
    extra = 33 if any(ord(c) > 127 for c in pwd) else 0
    bits = len(pwd) * (pools + extra).bit_length() if (pools + extra) else 0
    score = "слабый" if bits < 50 else "средний" if bits < 70 else "хороший" if bits < 90 else "отличный"
    return kv([("длина", len(pwd)), ("наборов символов", pools),
               ("энтропия", f"~{bits} бит"), ("оценка", score),
               ("совет", "12+ символов, 3+ класса, не словарное слово")])


@agent("sec.genpass", "Генератор паролей", "security",
       "Создаёт стойкий пароль через secrets (криптостойкий ГПСЧ)",
       keywords=("сгенерируй пароль", "genpass", "новый пароль", "случайный пароль"),
       examples=("20",), needs=(), secret=True)
def genpass(ctx: Context, text: str):
    n = int(text.strip() or 20) if text.strip().isdigit() else 20
    n = max(12, min(64, n))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(n))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in "!@#$%^&*()-_=+[]{}" for c in pwd)):
            return pwd


@agent("sec.hash", "Хэш", "security",
       "SHA-256/MD5 файла или строки — для сверки целостности",
       keywords=("хэш", "hash", "sha256", "md5", "контрольная сумма", "целостность"),
       examples=("файл=@homelab/homelab.json",), needs=())
def hash_agent(ctx: Context, text: str):
    from ..utils import parse_kv
    params, rest = parse_kv(text)
    target = params.get("файл") or params.get("file") or rest.strip()
    if not target:
        raise ValueError("укажи файл=путь или строку")
    if "/" in target or target.startswith("."):
        path = resolve_path(ctx, target)          # песочница
        if not path.is_file():
            raise ValueError(f"не файл: {target}")
        if path.stat().st_size > 512 * 1024 * 1024:
            raise ValueError("файл больше 512 МБ")
        sha, md5, sha1, size = (hashlib.sha256(), hashlib.md5(),
                                hashlib.sha1(), 0)
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                size += len(chunk)
                sha.update(chunk)
                md5.update(chunk)
                sha1.update(chunk)
        return kv([("источник", f"файл {path.name} ({human_bytes(size)})"),
                   ("sha256", sha.hexdigest()), ("md5", md5.hexdigest()),
                   ("sha1", sha1.hexdigest())])
    data = target.encode("utf-8")
    return kv([("источник", "строка"), ("sha256", hashlib.sha256(data).hexdigest()),
               ("md5", hashlib.md5(data).hexdigest()),
               ("sha1", hashlib.sha1(data).hexdigest())])


@agent("sec.headers", "Заголовки HTTP", "security",
       "Проверяет защитные заголовки локального веб-интерфейса",
       keywords=("заголовки", "headers", "hsts", "csp", "безопасность веба", "luci"),
       examples=("192.168.1.1",), needs=("net",))
def headers(ctx: Context, text: str):
    url = (text or "").strip().split()[0] if (text or "").strip() else "192.168.1.1"
    if "://" not in url:
        url = f"http://{url}"
    r = http_fetch(ctx, url, method="GET", timeout=4)
    if not r.get("status"):
        return f"{url}: нет ответа ({r.get('error', '')})"
    h = {k.lower(): v for k, v in r.get("headers", {}).items()}
    checks = [
        ("strict-transport-security", "HSTS"),
        ("content-security-policy", "CSP"),
        ("x-frame-options", "anti-clickjacking"),
        ("x-content-type-options", "nosniff"),
    ]
    rows = [[name, "есть" if key in h else "нет"] for key, name in checks]
    leaks = [f"{k}: {v}" for k, v in h.items()
             if k in ("server", "x-powered-by") and v]
    out = f"{url} → HTTP {r['status']}\n" + table(rows, ["заголовок", "статус"])
    if leaks:
        out += "\nутечка версий: " + "; ".join(leaks)
    return out


@agent("sec.logs", "Анализ логов", "security",
       "Ищет в логах неудачные входы, ошибки и подозрительные попытки",
       keywords=("логи", "log", "взлом", "неудачный вход", "ошибки", "failed password"),
       examples=("",), needs=())
def logs(ctx: Context, text: str):
    patterns = re.compile(
        r"(?i)(failed password|authentication failure|invalid user|"
        r"connection refused|permission denied|error|crit|panic)")
    roots = [Path("/var/log"), ctx.data / "logs"]
    hits, scanned = [], 0
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*"))[:60]:
            if not p.is_file() or p.stat().st_size > 2_000_000:
                continue
            if p.suffix not in (".log", ".txt", "") and "log" not in p.name:
                continue
            try:
                lines = p.read_text("utf-8", errors="replace").splitlines()
            except OSError:
                continue
            scanned += 1
            for n, line in enumerate(lines[-400:], 1):
                if patterns.search(line):
                    hits.append([p.name, len(lines) - 400 + n, line.strip()[:90]])
    if not hits:
        return f"проверено файлов: {scanned}, подозрительных строк не найдено"
    return (f"проверено {scanned} файлов, совпадений {len(hits)} "
            f"(последние 300 строк каждого):\n"
            + table(hits[:30], ["файл", "строка", "текст"], align_right={1}))


@agent("sec.manifest", "Манифест целостности", "security",
       "Считает SHA-256 всех файлов каталога и сохраняет манифест в data/",
       keywords=("манифест", "целостность", "контрольные суммы", "checksum", "сверка"),
       examples=("каталог=@homelab",), needs=("fs-write",))
def manifest(ctx: Context, text: str):
    from ..utils import parse_kv
    params, rest = parse_kv(text)
    raw = params.get("каталог") or params.get("dir") or rest or str(HOMELAB_DIR)
    base = resolve_path(ctx, raw)                 # песочница
    if not base.is_dir():
        raise ValueError(f"нет каталога {raw}")
    lines, total = [], 0
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for name in sorted(filenames):
            if total >= 3000:
                break
            p = Path(dirpath) / name
            try:
                if p.is_symlink() or p.stat().st_size >= 50_000_000:
                    continue
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                continue
            lines.append(f"{h}  {p.relative_to(base)}")
            total += 1
    out_path = ctx.out / "manifest.sha256"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", "utf-8")
    return (f"файлов: {total}, манифест: {out_path}\n"
            f"проверка позже: sec.hash файл={out_path}")
