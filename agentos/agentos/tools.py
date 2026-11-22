"""Безопасные инструменты: файлы в песочнице, whitelisted shell, LAN-проверки.

Никаких сторонних библиотек. Сеть — только локальный периметр из конфига.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .core import HOMELAB_DIR, ROOT, Context

# ---------------------------------------------------------------- shell
# Только команды, которые не читают и не пишут произвольные файлы.
# Любая работа с файлами — через resolve_path/read_text/write_text.
ALLOWED_CMDS = {
    "ping", "ip", "ss", "df", "uname", "uptime", "free", "ps", "date",
    "hostname", "which", "getent",
}
FORBIDDEN_ARGS = ("--upload-file", "-T", "--config", "-K", "rm", "mkfs", "dd")


class ToolError(RuntimeError):
    pass


def run_cmd(ctx: Context, argv: list[str], *, timeout: int | None = None,
            cwd: Path | None = None, check_args: bool = True) -> dict:
    """Запуск разрешённой команды без shell. Возвращает код/вывод."""
    if not ctx.cfg.get("safety", {}).get("allow_shell", True):
        raise ToolError("shell запрещён конфигом")
    if not argv:
        raise ToolError("пустая команда")
    base = Path(argv[0]).name
    if base.lower().endswith(".exe"):        # Windows: ping.exe == ping
        base = base[:-4]
    if base not in ALLOWED_CMDS:
        raise ToolError(f"команда {base!r} не разрешена")
    if check_args:
        for a in argv[1:]:
            for bad in FORBIDDEN_ARGS:
                if a == bad:
                    raise ToolError(f"аргумент {bad!r} запрещён")
    timeout = timeout or int(ctx.cfg.get("safety", {}).get("shell_timeout", 15))
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd or ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -1, "out": "", "err": f"таймаут {timeout}с"}
    except FileNotFoundError:
        return {"ok": False, "code": -1, "out": "", "err": f"нет команды {base}"}
    return {"ok": proc.returncode == 0, "code": proc.returncode,
            "out": proc.stdout.strip(), "err": proc.stderr.strip()}


# ---------------------------------------------------------------- Windows
def is_windows() -> bool:
    return os.name == "nt"


def decode_oem(data: bytes) -> str:
    """Вывод cmd.exe/powershell.exe в консольной кодировке (UTF-8 → cp866 → cp1251)."""
    if not data:
        return ""
    for enc in ("utf-8", "cp866", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def run_windows(argv: list[str], *, timeout: int = 60) -> dict:
    """Запуск cmd.exe/powershell.exe без shell-строки. Только на Windows."""
    if not is_windows():
        raise ToolError("этот агент работает только в Windows (сейчас не Windows)")
    if not argv:
        raise ToolError("пустая команда")
    exe = shutil.which(argv[0]) or argv[0]
    try:
        proc = subprocess.run([exe, *argv[1:]], capture_output=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -1, "out": "",
                "err": f"таймаут {timeout}с"}
    except FileNotFoundError:
        return {"ok": False, "code": -1, "out": "",
                "err": f"нет {argv[0]}"}
    return {"ok": proc.returncode == 0, "code": proc.returncode,
            "out": decode_oem(proc.stdout).strip(),
            "err": decode_oem(proc.stderr).strip()}


# ---------------------------------------------------------------- LAN
def is_local_host(host: str, network: str = "192.168.1.0/24") -> bool:
    """Строго: только канонический IP в LAN/loopback либо имя, все адреса
    которого в LAN. Числовые формы (2130706433, 0x7f000001) запрещены."""
    host = (host or "").strip().strip("[]")
    if not host:
        return False
    if host in ("localhost",):
        return True
    if re.fullmatch(r"\d+", host) or re.fullmatch(r"0[xX][0-9a-fA-F]+", host):
        return False                      # сокращённые/целочисленные IP — обход
    try:
        ip = ipaddress.ip_address(host)
        net = ipaddress.ip_network(network, strict=False)
        return ip.is_loopback or ip in net
    except ValueError:
        pass
    try:
        addrs = {ai[4][0] for ai in socket.getaddrinfo(host, None)}
    except (socket.gaierror, OSError):
        addrs = set()
    if not addrs:
        return host.endswith((".lan", ".local"))
    net = ipaddress.ip_network(network, strict=False)
    for a in addrs:
        ip = ipaddress.ip_address(a)
        if not (ip.is_loopback or ip in net):
            return False
    return True


def resolve(host: str, timeout: float = 2.0) -> list[str]:
    socket.setdefaulttimeout(timeout)
    try:
        return [ai[4][0] for ai in socket.getaddrinfo(host, None)]
    except (socket.gaierror, OSError):
        return []


def tcp_check(host: str, port: int, timeout: float = 1.2) -> dict:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return {"host": host, "port": int(port), "open": True}
    except (socket.timeout, OSError):
        return {"host": host, "port": int(port), "open": False}


def http_fetch(ctx: Context, url: str, *, method: str = "GET", timeout: float = 4.0,
               max_bytes: int = 200_000) -> dict:
    parsed = urllib.parse.urlparse(url if "://" in url else f"http://{url}")
    if parsed.scheme not in ("http", "https"):
        raise ToolError("только http/https")
    host = parsed.hostname or ""
    if not is_local_host(host, ctx.network):
        raise ToolError(f"{host} вне локальной сети {ctx.network}")
    req = urllib.request.Request(url, method=method,
                                 headers={"User-Agent": "agentos/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_bytes).decode("utf-8", "replace")
            return {"ok": True, "status": resp.status, "headers": dict(resp.headers),
                    "body": body, "url": resp.geturl()}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "headers": dict(exc.headers),
                "body": exc.read(max_bytes).decode("utf-8", "replace"), "url": url}
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        return {"ok": False, "status": 0, "error": str(exc), "url": url}


# ---------------------------------------------------------------- файлы
def _inside(path: Path, roots: list[Path]) -> bool:
    path = path.resolve()
    norm = os.path.normcase(str(path)) if os.name == "nt" else None
    for root in roots:
        resolved = root.resolve()
        try:
            path.relative_to(resolved)
            return True
        except ValueError:
            if norm:
                r = os.path.normcase(str(resolved))
                if norm == r or norm.startswith(r + os.sep):
                    return True
            continue
    return False


def resolve_path(ctx: Context, raw: str, *, write: bool = False) -> Path:
    """Путь относительно workspace; запись только в data/out (ctx.data, ctx.out)."""
    raw = (raw or "").strip()
    norm = raw.replace("\\", "/")            # @app\docs работает и на Windows
    for alias, base in (("@app", ROOT), ("@homelab", HOMELAB_DIR)):
        if norm == alias or norm.startswith(alias + "/"):
            raw = str(base) + norm[len(alias):]
    p = Path(os.path.expanduser(raw))
    if not p.is_absolute():
        parts = p.parts
        if write:
            if parts and parts[0] == "data":
                p = ctx.data.joinpath(*parts[1:])
            elif parts and parts[0] == "out":
                p = ctx.out.joinpath(*parts[1:])
            else:
                p = ctx.out / p
        else:
            p = ROOT / p
    read_roots = [ROOT, HOMELAB_DIR, Path(tempfile.gettempdir()) / "opencode",
                  ctx.data, ctx.out]
    if write and not _inside(p, [ctx.data, ctx.out]):
        raise ToolError("запись разрешена только в data/ и out/")
    if not write and not _inside(p, read_roots):
        raise ToolError("чтение вне разрешённых каталогов")
    return p.resolve()


def read_text(ctx: Context, raw: str, *, limit: int | None = None) -> str:
    path = resolve_path(ctx, raw)
    if not path.exists():
        raise ToolError(f"нет файла: {raw}")
    if path.is_dir():
        raise ToolError(f"это каталог: {raw}")
    limit = limit or int(ctx.cfg.get("safety", {}).get("max_read_bytes", 400_000))
    with path.open("rb") as fh:
        data = fh.read(limit)
    return data.decode("utf-8", "replace")


def write_text(ctx: Context, raw: str, text: str) -> Path:
    path = resolve_path(ctx, raw, write=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")
    return path


PROJECT_DOCS = {"CATALOG.md"}


def write_project(ctx: Context, name: str, text: str) -> Path:
    """Запись служебных документов проекта строго по белому списку."""
    if name not in PROJECT_DOCS:
        raise ToolError(f"{name} не входит в список проектных документов")
    if ctx.dry_run:
        raise ToolError("dry-run: запись отключена")
    path = ROOT / name
    path.write_text(text, "utf-8")
    return path


def write_json(ctx: Context, raw: str, obj) -> Path:
    return write_text(ctx, raw, json.dumps(obj, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- homelab
def homelab(ctx: Context, args: list[str], *, timeout: int = 180) -> dict:
    """Вызов штатного CLI homelab.py (сеть, HA, ADB, камеры, бэкапы)."""
    script = HOMELAB_DIR / "homelab.py"
    if not script.exists():
        raise ToolError("homelab.py не найден")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args], cwd=str(HOMELAB_DIR),
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -1, "out": "", "err": f"таймаут {timeout}с"}
    return {"ok": proc.returncode == 0, "code": proc.returncode,
            "out": proc.stdout.strip(), "err": proc.stderr.strip()}
