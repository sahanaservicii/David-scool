#!/usr/bin/env python3
"""
homelab — офлайн-инструментарий для домашней инфраструктуры.

Только стандартная библиотека Python: работает без интернета, подписок и
внешних сервисов. Всё общение — с локальной сетью (LAN) по SSH/HTTP/ADB.

Команды:
  doctor                 проверить доступность роутера, HA, ТВ, телефона
  scan                   просканировать LAN и сохранить результат
  inventory              показать известные устройства и найденные хосты
  ha ...                 Home Assistant REST API (states/state/call/template/...)
  router ...             OpenWrt по SSH (status/exec/uci/backup)
  adb ...                Android по TCP (devices/shell/key/text/screencap)
  tv ...                 то же, что adb, но цель по умолчанию — Android TV
  phone ...              то же, что adb, но цель по умолчанию — телефон
  cam <ip>               проба IP-камеры/NVR (HTTP, RTSP, ONVIF-порт)
  backup                 локальный бэкап конфигов/состояния (+ роутер, HA)
  report                 отчёт по сети в Markdown
  notify                 уведомление на этот Android-телефон (локальный мост)

Секреты НЕ хранятся в этом каталоге. Файл:
  ~/.config/opencode/secrets/homelab.env   (chmod 600)
Ключи: HASS_TOKEN, HOMELAB_SSH_KEY, ROUTER_PASSWORD (не используется sshpass —
нужен SSH-ключ), ADB_* при необходимости.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "homelab.json"
STATE_DIR = ROOT / "state"
BACKUP_DIR = ROOT / "backups"
REPORT_DIR = ROOT.parent / "reports"
SECRETS_PATH = Path(
    os.environ.get("OPENCODE_CONFIG_HOME", str(Path.home() / ".config" / "opencode"))
) / "secrets" / "homelab.env"

SCAN_PORTS = [
    22, 53, 80, 443, 445, 554, 1883, 5000, 5555, 7000, 8000, 8008, 8009,
    8080, 8081, 8123, 8443, 9000, 9100, 32400, 3389, 34567,
]
DESTRUCTIVE = re.compile(
    r"(rm\s+-rf|mkfs|dd\s+if=|sysupgrade|reboot|poweroff|fw4\s+restart|"
    r"iptables-restore|nft\s+flush|dropbear|passwd|opkg\s+remove)",
    re.I,
)


# ---------------------------------------------------------------- утилиты
def load_secrets() -> None:
    """Читает KEY=VALUE из секретного файла, не перезаписывая окружение."""
    if not SECRETS_PATH.exists():
        return
    try:
        for line in SECRETS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        die(f"нет {CONFIG_PATH}", 2)
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"ошибка JSON в {CONFIG_PATH}: {e}", 2)
    cfg.setdefault("network", "192.168.1.0/24")
    cfg.setdefault("android", [])
    return cfg


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def die(msg: str, code: int = 1) -> None:
    print(f"ОШИБКА: {msg}", file=sys.stderr)
    raise SystemExit(code)


def human_ts(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or time.time()).strftime("%Y-%m-%d %H:%M:%S")


def ok(flag: bool) -> str:
    return "OK" if flag else "FAIL"


def emit(obj, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- сеть
def local_ip_toward(host: str, port: int = 80) -> str:
    """Локальный IP, через который пойдёт трафик к host (видно, работает ли VPN)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((host, port))
        return s.getsockname()[0]
    except OSError:
        return "нет маршрута"
    finally:
        s.close()


def tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, int(port))) == 0
    except (OSError, ValueError):
        return False
    finally:
        s.close()


def http_get(host: str, port: int, path: str = "/", timeout: float = 4.0) -> dict:
    """Минимальный HTTP-запрос без зависимостей."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(
                f"GET {path} HTTP/1.0\r\nHost: {host}\r\n"
                f"User-Agent: homelab/1.0\r\nConnection: close\r\n\r\n".encode()
            )
            chunks, total = [], 0
            while total < 65536:
                b = s.recv(8192)
                if not b:
                    break
                chunks.append(b)
                total += len(b)
        raw = b"".join(chunks)
        head, _, body = raw.partition(b"\r\n\r\n")
        lines = head.decode("latin-1", "replace").split("\r\n")
        status = int(lines[0].split()[1]) if lines and len(lines[0].split()) > 1 else 0
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        title = ""
        m = re.search(rb"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        if m:
            title = m.group(1).decode("utf-8", "replace").strip()[:120]
        return {"status": status, "headers": headers, "server": headers.get("server", ""),
                "title": title, "body": body[:4096]}
    except (OSError, ValueError) as e:
        return {"status": 0, "error": str(e), "headers": {}, "server": "", "title": "", "body": b""}


def rtsp_probe(host: str, port: int = 554, timeout: float = 4.0) -> dict:
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(
                f"OPTIONS rtsp://{host}:{port}/ RTSP/1.0\r\nCSeq: 1\r\n"
                f"User-Agent: homelab/1.0\r\n\r\n".encode()
            )
            data = s.recv(4096)
        text = data.decode("latin-1", "replace")
        return {"ok": text.startswith("RTSP/"), "status": text.split("\r\n", 1)[0],
                "server": next((l for l in text.split("\r\n") if l.lower().startswith("server:")), "")}
    except OSError as e:
        return {"ok": False, "error": str(e)}


def scan_host(host: str, ports: list[int], timeout: float) -> list[int]:
    found = []
    for p in ports:
        if tcp_open(host, p, timeout):
            found.append(p)
    return found


def cmd_scan(args) -> None:
    cfg = load_config()
    net = cfg["network"]
    if args.hosts:
        hosts = [h.strip() for h in args.hosts.split(",") if h.strip()]
        net = "custom"
    else:
        m = re.match(r"^(\d+\.\d+\.\d+)\.\d+/\d+$", net)
        if not m:
            die(f"не понимаю сеть {net!r}; ожидается вид 192.168.1.0/24")
        prefix = m.group(1)
        hosts = [f"{prefix}.{i}" for i in range(1, 255)]
    ports = [int(p) for p in args.ports.split(",")] if args.ports else SCAN_PORTS
    started = time.time()
    print(f"Сканирую {len(hosts)} хостов, {len(ports)} портов…", file=sys.stderr)
    result: dict[str, list[int]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(scan_host, h, ports, args.timeout): h for h in hosts}
        for fut in futures:
            h = futures[fut]
            try:
                open_ports = fut.result()
            except Exception:
                open_ports = []
            if open_ports:
                result[h] = open_ports
                print(f"  {h:<15} {' '.join(map(str, open_ports))}", file=sys.stderr)
    payload = {
        "timestamp": human_ts(started),
        "network": net,
        "ports": ports,
        "count": len(result),
        "hosts": dict(sorted(result.items(), key=lambda kv: tuple(map(int, kv[0].split("."))))),
    }
    save_json(STATE_DIR / "scan.json", payload)
    if args.json:
        emit(payload, True)
    else:
        print(f"Найдено хостов: {len(result)}   ({payload['timestamp']})")
        for ip, ports in payload["hosts"].items():
            print(f"  {ip:<15} {' '.join(map(str, ports))}")
        print(f"Сохранено: {STATE_DIR / 'scan.json'}")
    print(f"Готово за {time.time() - started:.1f} с, найдено {len(result)} хостов.",
          file=sys.stderr)


def load_scan() -> dict:
    p = STATE_DIR / "scan.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------- SSH / OpenWrt
def ssh_router(cfg: dict, command: str, timeout: int = 25) -> subprocess.CompletedProcess:
    r = cfg.get("router", {})
    host = r.get("host", cfg.get("gateway", "192.168.1.1"))
    user = r.get("user", "root")
    port = int(r.get("port", 22))
    key = os.environ.get("HOMELAB_SSH_KEY") or r.get("identity")
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6",
        "-o", "StrictHostKeyChecking=accept-new", "-p", str(port),
    ]
    if key:
        cmd += ["-i", os.path.expanduser(key)]
    cmd += [f"{user}@{host}", command]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def cmd_router(args) -> None:
    cfg = load_config()
    sub = args.router_cmd

    if sub == "status":
        script = (
            "echo '### system'; ubus call system board 2>/dev/null | head -40; "
            "echo '### uptime'; uptime; "
            "echo '### memory'; free -m 2>/dev/null || cat /proc/meminfo | head -3; "
            "echo '### disk'; df -h / /tmp 2>/dev/null; "
            "echo '### wan'; ubus call network.interface.wan status 2>/dev/null | head -40; "
            "echo '### wifi'; iwinfo 2>/dev/null | head -20; "
            "echo '### dhcp leases'; cat /tmp/dhcp.leases 2>/dev/null | tail -40"
        )
        try:
            p = ssh_router(cfg, script, timeout=30)
        except subprocess.TimeoutExpired:
            die("SSH к роутеру не ответил за 30 с")
        print(p.stdout or "", end="")
        if p.returncode != 0:
            die(f"SSH код {p.returncode}: {p.stderr.strip()[:500]}")
        return

    if sub == "exec":
        command = " ".join(args.remote)
        if not command:
            die("router exec требует команду, например: router exec 'ubus call system info'")
        if DESTRUCTIVE.search(command) and not args.yes:
            die("команда выглядит разрушительной. Повтори с --yes, если это осознанно")
        try:
            p = ssh_router(cfg, command, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            die(f"SSH таймаут ({args.timeout} с)")
        print(p.stdout or "", end="")
        if p.stderr:
            print(p.stderr, file=sys.stderr, end="")
        raise SystemExit(p.returncode)

    if sub == "uci":
        cmd = "uci show " + " ".join(args.remote)
        p = ssh_router(cfg, cmd, timeout=20)
        print(p.stdout or "", end="")
        if p.returncode:
            die(p.stderr.strip()[:500])
        return

    if sub == "backup":
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        dest = BACKUP_DIR / f"openwrt-{datetime.now():%Y%m%d-%H%M%S}.tar.gz"
        try:
            p = subprocess.run(ssh_router_cmd(cfg) + ["sysupgrade -b -"],
                               capture_output=True, timeout=90)
        except subprocess.TimeoutExpired:
            die("роутер не отдал архив за 90 с")
        data = p.stdout
        if p.returncode != 0 or not data:
            die(f"не удалось получить архив OpenWrt: {p.stderr.decode('utf-8', 'replace')[:300]}")
        dest.write_bytes(data)
        print(f"Бэкап роутера: {dest} ({len(data)} байт)")
        return

    die(f"неизвестная подкоманда router: {sub}", 2)


def ssh_router_cmd(cfg: dict) -> list[str]:
    r = cfg.get("router", {})
    host = r.get("host", cfg.get("gateway", "192.168.1.1"))
    user = r.get("user", "root")
    port = int(r.get("port", 22))
    key = os.environ.get("HOMELAB_SSH_KEY") or r.get("identity")
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6",
           "-o", "StrictHostKeyChecking=accept-new", "-p", str(port)]
    if key:
        cmd += ["-i", os.path.expanduser(key)]
    cmd += [f"{user}@{host}"]
    return cmd


# ---------------------------------------------------------------- Home Assistant
def ha_url(cfg: dict) -> str:
    return cfg.get("home_assistant", {}).get("url", "http://192.168.1.127:8123").rstrip("/")


def ha_request(cfg: dict, method: str, path: str, data=None, timeout: float = 15.0):
    token = os.environ.get("HASS_TOKEN", "")
    if not token:
        die(f"нет HASS_TOKEN. Создай токен в HA (Профиль → Токены) и запиши в {SECRETS_PATH}")
    url = ha_url(cfg) + (path if path.startswith("/") else "/" + path)
    body = None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if data is not None:
        body = json.dumps(data).encode()
    req = request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if "json" in ctype:
                return json.loads(raw.decode("utf-8", "replace"))
            return raw.decode("utf-8", "replace")
    except error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        die(f"HA HTTP {e.code} на {method} {path}: {detail}")
    except error.URLError as e:
        die(f"HA недоступен по {ha_url(cfg)}: {e.reason}. Проверь Wi-Fi и адрес в homelab.json")
    except (TimeoutError, socket.timeout):
        die(f"HA не ответил за {timeout} с")


def json_arg(raw: str | None):
    """JSON из строки или из файла через @path."""
    if not raw:
        return None
    if raw.startswith("@"):
        return json.loads(Path(raw[1:]).read_text(encoding="utf-8"))
    return json.loads(raw)


def cmd_ha(args) -> None:
    cfg = load_config()
    sub = args.ha_cmd
    if sub == "states":
        states = ha_request(cfg, "GET", "/api/states")
        if args.domain:
            states = [s for s in states if s["entity_id"].startswith(args.domain + ".")]
        if args.json:
            print(json.dumps(states, ensure_ascii=False, indent=2))
            return
        print(f"Сущностей: {len(states)}")
        bad = [s for s in states if s["state"] in ("unavailable", "unknown")]
        for s in states[: args.limit]:
            name = s.get("attributes", {}).get("friendly_name", "")
            print(f"  {s['entity_id']:<48} {s['state']:<12} {name}")
        if len(states) > args.limit:
            print(f"  … ещё {len(states) - args.limit}")
        if bad:
            print(f"\nНедоступно/неизвестно: {len(bad)}")
            for s in bad[:15]:
                print(f"  {s['entity_id']}")
        return

    if sub == "state":
        s = ha_request(cfg, "GET", f"/api/states/{args.entity}")
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return

    if sub == "call":
        data = json_arg(args.data) or {}
        res = ha_request(cfg, "POST", f"/api/services/{args.domain}/{args.service}", data)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    if sub == "template":
        res = ha_request(cfg, "POST", "/api/template", {"template": args.text})
        print(res)
        return

    if sub == "config":
        print(json.dumps(ha_request(cfg, "GET", "/api/config"), ensure_ascii=False, indent=2))
        return

    if sub == "errors":
        print(ha_request(cfg, "GET", "/api/error_log"))
        return

    if sub == "services":
        print(json.dumps(ha_request(cfg, "GET", "/api/services"), ensure_ascii=False, indent=2))
        return

    if sub == "raw":
        data = json_arg(args.data)
        res = ha_request(cfg, args.method, args.path, data)
        print(res if isinstance(res, str) else json.dumps(res, ensure_ascii=False, indent=2))
        return

    die(f"неизвестная подкоманда ha: {sub}", 2)


# ---------------------------------------------------------------- Android ADB (TCP)
CMD_CNXN = struct.unpack("<I", b"CNXN")[0]
CMD_AUTH = struct.unpack("<I", b"AUTH")[0]
CMD_OPEN = struct.unpack("<I", b"OPEN")[0]
CMD_OKAY = struct.unpack("<I", b"OKAY")[0]
CMD_CLSE = struct.unpack("<I", b"CLSE")[0]
CMD_WRTE = struct.unpack("<I", b"WRTE")[0]
A_VERSION = 0x01000001


class AdbError(RuntimeError):
    pass


def _packet(cmd: int, a0: int, a1: int, payload: bytes = b"") -> bytes:
    return struct.pack(
        "<IIIIII", cmd, a0, a1, len(payload), sum(payload) & 0xFFFFFFFF,
        cmd ^ 0xFFFFFFFF,
    ) + payload


def _recv_exact(s: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise AdbError("соединение ADB закрыто")
        buf += chunk
    return buf


def _read_packet(s: socket.socket) -> tuple[int, int, int, bytes]:
    hdr = _recv_exact(s, 24)
    cmd, a0, a1, ln, _sum, magic = struct.unpack("<IIIIII", hdr)
    if cmd ^ 0xFFFFFFFF != magic:
        raise AdbError("повреждён пакет ADB (magic)")
    data = _recv_exact(s, ln) if ln else b""
    return cmd, a0, a1, data


def adb_connect(host: str, port: int = 5555, timeout: float = 6.0) -> socket.socket:
    s = socket.create_connection((host, port), timeout=timeout)
    s.settimeout(timeout)
    s.sendall(_packet(CMD_CNXN, A_VERSION, 4096, b"host::\x00"))
    cmd, _a0, _a1, data = _read_packet(s)
    if cmd == CMD_AUTH:
        s.close()
        raise AdbError(
            "устройство требует авторизацию ADB. Подтверди ключ на экране ТВ/телефона "
            "или включи «Отладка по сети» заново. Без adb-ключа доступ не получится."
        )
    if cmd != CMD_CNXN:
        s.close()
        raise AdbError(f"неожиданный ответ ADB: {cmd:#x}")
    return s


def adb_shell(host: str, command: str, port: int = 5555, timeout: float = 12.0,
              raw: bool = False):
    s = adb_connect(host, port, timeout)
    try:
        s.sendall(_packet(CMD_OPEN, 1, 0, f"shell:{command}\x00".encode()))
        cmd, _a0, _a1, _data = _read_packet(s)
        if cmd != CMD_OKAY:
            raise AdbError("устройство отклонило shell-сессию")
        out = bytearray()
        idle_since = time.time()
        while True:
            try:
                cmd, _a0, _a1, data = _read_packet(s)
            except socket.timeout:
                break
            if cmd == CMD_WRTE:
                out += data
                s.sendall(_packet(CMD_OKAY, 1, 0))
                idle_since = time.time()
            elif cmd == CMD_CLSE:
                break
            elif cmd == CMD_OKAY:
                continue
            if time.time() - idle_since > timeout:
                break
        return bytes(out) if raw else bytes(out).decode("utf-8", "replace")
    finally:
        s.close()


def resolve_target(cfg: dict, name_or_host: str | None, default: str = "tv") -> tuple[str, int, str]:
    name = name_or_host or default
    for dev in cfg.get("android", []):
        if name in (dev.get("name"), dev.get("host"), dev.get("alias")):
            return dev["host"], int(dev.get("port", 5555)), dev.get("name", name)
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", name):
        return name, 5555, name
    die(f"неизвестное Android-устройство {name!r}; добавь его в homelab.json → android")


def cmd_adb(args) -> None:
    cfg = load_config()
    host, port, name = resolve_target(cfg, args.target, args.default_target or "tv")
    sub = args.adb_cmd

    if sub == "devices":
        devices = []
        for dev in cfg.get("android", []):
            h, p = dev["host"], int(dev.get("port", 5555))
            entry = {"name": dev.get("name"), "host": h, "port": p, "reachable": False}
            if tcp_open(h, p, 1.0):
                entry["reachable"] = True
                try:
                    s = adb_connect(h, p, 5)
                    s.close()
                    entry["adb"] = "ok"
                    entry["model"] = adb_shell(h, "getprop ro.product.model", p, 5).strip()
                except AdbError as e:
                    entry["adb"] = str(e)
            devices.append(entry)
        print(json.dumps(devices, ensure_ascii=False, indent=2))
        return

    try:
        if sub == "shell":
            print(adb_shell(host, " ".join(args.command), port, 12), end="")
        elif sub == "key":
            print(adb_shell(host, f"input keyevent {args.code}", port, 6), end="")
        elif sub == "text":
            text = " ".join(args.command).replace(" ", "%s")
            print(adb_shell(host, f"input text {text}", port, 6), end="")
        elif sub == "reboot":
            if not args.yes:
                die("reboot требует --yes")
            adb_shell(host, "reboot", port, 5)
            print(f"{name}: команда перезагрузки отправлена")
        elif sub == "screencap":
            data = adb_shell(host, "screencap -p", port, 30, raw=True)
            if data.startswith(b"\r\n"):
                data = data[2:]
            data = data.replace(b"\r\n", b"\n")
            dest = Path(args.file)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            print(f"Скриншот: {dest} ({len(data)} байт)")
        else:
            die(f"неизвестная подкоманда adb: {sub}", 2)
    except AdbError as e:
        die(f"{name} ({host}:{port}): {e}")
    except (OSError, socket.timeout) as e:
        die(f"{name} ({host}:{port}) недоступен: {e}")


# ---------------------------------------------------------------- камеры
def cmd_cam(args) -> None:
    host = args.ip
    ports = [80, 554, 34567, 8000, 8080]
    open_ports = [p for p in ports if tcp_open(host, p, 0.8)]
    info = {"host": host, "open_ports": open_ports, "http": None, "rtsp": None}
    if 80 in open_ports:
        h = http_get(host, 80, "/")
        info["http"] = {"status": h.get("status"), "server": h.get("server"),
                        "title": h.get("title")}
    if 554 in open_ports:
        info["rtsp"] = rtsp_probe(host, 554)
    print(json.dumps(info, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- doctor
def cmd_doctor(args) -> None:
    cfg = load_config()
    gw = cfg.get("gateway", "192.168.1.1")
    if getattr(args, "wait", 0):
        deadline = time.time() + args.wait
        print(f"Жду домашнюю сеть до {args.wait} с…", flush=True)
        while time.time() < deadline:
            if any(tcp_open(gw, p, 1.0) for p in (80, 22, 53)):
                print("Сеть появилась.", flush=True)
                break
            time.sleep(5)
        else:
            print("Сеть не появилась за отведённое время.", flush=True)
    rows = []

    def check(name: str, fn, enabled: bool = True):
        if not enabled:
            rows.append((name, "skip", "отложено (enabled=false)"))
            return
        try:
            detail = fn()
            rows.append((name, "ok", detail))
        except SystemExit as e:  # die() внутри проверки не должен убивать doctor
            rows.append((name, "fail", f"код {e.code}"))
        except Exception as e:  # noqa: BLE001 — диагностика должна пережить всё
            rows.append((name, "fail", str(e)[:160]))

    def gateway():
        gw = cfg.get("gateway", "192.168.1.1")
        ports = [p for p in (22, 80, 443) if tcp_open(gw, p, 1.2)]
        if not ports:
            raise RuntimeError(f"{gw} не отвечает по TCP")
        return f"{gw}: {', '.join(map(str, ports))}"

    def router():
        p = ssh_router(cfg, "echo ok", timeout=10)
        if p.returncode:
            raise RuntimeError((p.stderr or "SSH без ключа/пароля").strip()[:120])
        return "SSH работает"

    def ha():
        url = ha_url(cfg)
        m = re.match(r"https?://([^/:]+)(?::(\d+))?", url)
        if not m:
            raise RuntimeError(f"странный URL {url}")
        h, p = m.group(1), int(m.group(2) or (443 if url.startswith("https") else 80))
        if not tcp_open(h, p, 2):
            raise RuntimeError(f"{h}:{p} недоступен")
        token = os.environ.get("HASS_TOKEN")
        if not token:
            return f"{h}:{p} открыт, но HASS_TOKEN не задан"
        data = ha_request(cfg, "GET", "/api/", timeout=6)
        msg = data.get("message", data) if isinstance(data, dict) else data
        return f"API отвечает: {msg}"

    def tv():
        dev = next((d for d in cfg.get("android", []) if d.get("name") == "tv"), None)
        if not dev:
            raise RuntimeError("нет устройства 'tv' в homelab.json")
        if not tcp_open(dev["host"], int(dev.get("port", 5555)), 2):
            raise RuntimeError(f"{dev['host']} недоступен (ADB выключен?)")
        s = adb_connect(dev["host"], int(dev.get("port", 5555)), 5)
        s.close()
        return "ADB-соединение установлено"

    def bridge():
        script = Path(os.environ.get("OPENCODE_CONFIG_HOME", str(Path.home() / ".config/opencode"))) / \
            "skills/android-device/android_device.py"
        if not script.exists():
            raise RuntimeError("нет android_device.py")
        p = subprocess.run([sys.executable, str(script), "health"], capture_output=True,
                           text=True, timeout=10)
        if p.returncode:
            raise RuntimeError(p.stderr.strip()[:120] or "мост не отвечает")
        return "локальный мост устройства работает"

    check("Шлюз", gateway)
    check("Роутер SSH", router)
    check("Home Assistant", ha, enabled=cfg.get("home_assistant", {}).get("enabled", True))
    check("Android TV ADB", tv)
    check("Мост телефона", bridge)

    gw = cfg.get("gateway", "192.168.1.1")
    print(f"Домашняя сеть: {cfg['network']}   проверка {human_ts()}")
    print(f"Локальный адрес для {gw}: {local_ip_toward(gw)}\n")
    marks = {"ok": "OK", "fail": "!!", "skip": "--"}
    for name, status, detail in rows:
        print(f"  [{marks[status]}] {name:<22} {detail}")
    failed = [n for n, s, _ in rows if s == "fail"]
    skipped = [n for n, s, _ in rows if s == "skip"]
    print()
    if failed:
        print(f"Проблемы: {', '.join(failed)}. Смотри README и secrets/homelab.env.")
        raise SystemExit(1)
    print("Критичных проблем нет." + (f" Отложено: {', '.join(skipped)}." if skipped else ""))


# ---------------------------------------------------------------- inventory / report
def cmd_inventory(args) -> None:
    cfg = load_config()
    scan = load_scan()
    known = {}
    for section in ("router", "home_assistant", "android", "cameras", "other"):
        items = cfg.get(section)
        if isinstance(items, dict):
            items = [dict(items, name=section)]
        for item in items or []:
            if not isinstance(item, dict) or not item.get("host"):
                continue
            known[item["host"]] = {
                "name": item.get("name") or item.get("host"),
                "kind": item.get("kind") or section,
                "note": item.get("note", ""),
                "ports": scan.get("hosts", {}).get(item["host"], []),
            }
    unknown = {
        ip: ports for ip, ports in scan.get("hosts", {}).items() if ip not in known
    }
    payload = {
        "scan_time": scan.get("timestamp"),
        "known": known,
        "unknown": unknown,
        "count_known": len(known),
        "count_unknown": len(unknown),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"Известные устройства ({len(known)}):")
    for ip, d in sorted(known.items()):
        ports = ",".join(map(str, d["ports"])) or "—"
        print(f"  {ip:<15} {d['kind']:<14} {d['name']:<22} {ports}")
    if unknown:
        print(f"\nНе описаны в homelab.json ({len(unknown)}):")
        for ip, ports in sorted(unknown.items()):
            print(f"  {ip:<15} {','.join(map(str, ports))}")
    if scan:
        print(f"\nПоследнее сканирование: {scan.get('timestamp')}")


def cmd_report(args) -> None:
    cfg = load_config()
    scan = load_scan()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    dest = REPORT_DIR / f"network-{datetime.now():%Y%m%d-%H%M}.md"
    lines = [
        "# Отчёт по домашней сети",
        "",
        f"- Дата: {human_ts()}",
        f"- Сеть: `{cfg['network']}`",
        f"- Шлюз: `{cfg.get('gateway', '192.168.1.1')}`",
        f"- Сканирование: {scan.get('timestamp') or 'не выполнялось'}",
        "",
        "## Хосты с открытыми портами",
        "",
        "| IP | Порты |",
        "|---|---|",
    ]
    for ip, ports in scan.get("hosts", {}).items():
        lines.append(f"| {ip} | {', '.join(map(str, ports))} |")
    if not scan.get("hosts"):
        lines.append("| — | нет данных, запусти `homelab.py scan` |")
    lines += ["", "## Настройки", "", "```json",
              json.dumps({k: v for k, v in cfg.items() if k != "secrets"},
                         ensure_ascii=False, indent=2), "```", ""]
    dest.write_text("\n".join(lines), encoding="utf-8")
    print(f"Отчёт: {dest}")


# ---------------------------------------------------------------- backup
def cmd_backup(args) -> None:
    cfg = load_config()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"homelab-{stamp}.tar.gz"
    manifest = {"created": human_ts(), "files": [], "router": None, "ha": None}
    with tarfile.open(dest, "w:gz") as tar:
        for p in (CONFIG_PATH, STATE_DIR / "scan.json", ROOT / "README.md",
                  ROOT / "INVENTORY.md", ROOT / "RUNBOOK.md", ROOT / "CHANGELOG.md"):
            if p.exists():
                tar.add(p, arcname=str(p.relative_to(ROOT)))
                manifest["files"].append(str(p.relative_to(ROOT)))
    if args.with_router:
        try:
            p = subprocess.run(ssh_router_cmd(cfg) + ["sysupgrade -b -"], capture_output=True,
                               timeout=60)
            if p.returncode == 0 and p.stdout:
                rb = BACKUP_DIR / f"openwrt-{stamp}.tar.gz"
                rb.write_bytes(p.stdout)
                manifest["router"] = rb.name
                print(f"Бэкап роутера: {rb}")
            else:
                manifest["router"] = "ошибка SSH"
        except Exception as e:  # noqa: BLE001
            manifest["router"] = f"ошибка: {e}"[:160]
    if args.with_ha:
        try:
            cfgdata = ha_request(cfg, "GET", "/api/config")
            hb = BACKUP_DIR / f"ha-config-{stamp}.json"
            hb.write_text(json.dumps(cfgdata, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest["ha"] = hb.name
            print(f"Конфиг HA: {hb}")
        except SystemExit:
            manifest["ha"] = "ошибка: HA/токен"
    manifest["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
    save_json(BACKUP_DIR / f"homelab-{stamp}.json", manifest)
    print(f"Локальный бэкап: {dest} ({dest.stat().st_size} байт)")


# ---------------------------------------------------------------- notify
def cmd_notify(args) -> None:
    script = Path(os.environ.get("OPENCODE_CONFIG_HOME", str(Path.home() / ".config/opencode"))) / \
        "skills/android-device/android_device.py"
    if not script.exists():
        die("нет локального моста android_device.py")
    cmd = [sys.executable, str(script), "notify", "--title", args.title,
           "--message", args.message]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    print(p.stdout.strip() or p.stderr.strip())
    raise SystemExit(p.returncode)


# ---------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="homelab.py",
        description="Офлайн-инструменты для домашней сети, HA, OpenWrt и Android.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Подробности: {ROOT / 'README.md'}",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="проверить доступность всех узлов")
    d.add_argument("--wait", type=int, default=0,
                   help="ждать появления LAN до N секунд (для WireGuard)")
    d.set_defaults(func=cmd_doctor)

    s = sub.add_parser("scan", help="просканировать LAN")
    s.add_argument("--hosts", help="список IP через запятую вместо всей подсети")
    s.add_argument("--ports", help="порты через запятую")
    s.add_argument("--timeout", type=float, default=0.8, help="таймаут на порт, с")
    s.add_argument("--workers", type=int, default=100)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_scan)

    inv = sub.add_parser("inventory", help="известные и неизвестные устройства")
    inv.add_argument("--json", action="store_true")
    inv.set_defaults(func=cmd_inventory)

    ha = sub.add_parser("ha", help="Home Assistant REST API")
    hs = ha.add_subparsers(dest="ha_cmd", required=True)
    a = hs.add_parser("states", help="список сущностей")
    a.add_argument("--domain")
    a.add_argument("--limit", type=int, default=40)
    a.add_argument("--json", action="store_true")
    a = hs.add_parser("state", help="состояние одной сущности")
    a.add_argument("entity")
    a = hs.add_parser("call", help="вызвать сервис")
    a.add_argument("domain")
    a.add_argument("service")
    a.add_argument("--data", help='JSON, например \'{"entity_id":"light.x"}\'')
    a = hs.add_parser("template", help="выполнить Jinja2-шаблон")
    a.add_argument("text")
    for name, desc in (("config", "конфигурация HA"), ("errors", "журнал ошибок"),
                       ("services", "доступные сервисы")):
        hs.add_parser(name, help=desc)
    a = hs.add_parser("raw", help="произвольный запрос")
    a.add_argument("method")
    a.add_argument("path")
    a.add_argument("--data")
    ha.set_defaults(func=cmd_ha)

    r = sub.add_parser("router", help="OpenWrt по SSH")
    rs = r.add_subparsers(dest="router_cmd", required=True)
    rs.add_parser("status", help="сводка: система, WAN, Wi-Fi, DHCP")
    a = rs.add_parser("exec", help="выполнить команду на роутере")
    a.add_argument("remote", nargs=argparse.REMAINDER)
    a.add_argument("--yes", action="store_true", help="подтвердить разрушительную команду")
    a.add_argument("--timeout", type=int, default=60)
    a = rs.add_parser("uci", help="uci show <path>")
    a.add_argument("remote", nargs=argparse.REMAINDER)
    rs.add_parser("backup", help="sysupgrade -b в backups/")
    r.set_defaults(func=cmd_router)

    for name, default in (("adb", None), ("tv", "tv"), ("phone", "phone")):
        a = sub.add_parser(name, help=f"Android ADB (по умолчанию: {default or 'tv'})")
        a.set_defaults(default_target=default)
        a.add_argument("--target", help="имя из homelab.json или IP")
        asub = a.add_subparsers(dest="adb_cmd", required=True)
        asub.add_parser("devices", help="проверить все Android-устройства")
        b = asub.add_parser("shell", help="shell-команда (одна строка)")
        b.add_argument("command", nargs="+")
        b = asub.add_parser("key", help="keyevent, например 3 = HOME")
        b.add_argument("code")
        b = asub.add_parser("text", help="ввести текст")
        b.add_argument("command", nargs="+")
        b = asub.add_parser("screencap", help="снять скриншот")
        b.add_argument("file")
        b = asub.add_parser("reboot", help="перезагрузить")
        b.add_argument("--yes", action="store_true")
        a.set_defaults(func=cmd_adb)

    c = sub.add_parser("cam", help="проба камеры/NVR")
    c.add_argument("ip")
    c.set_defaults(func=cmd_cam)

    b = sub.add_parser("backup", help="локальный бэкап")
    b.add_argument("--with-router", action="store_true")
    b.add_argument("--with-ha", action="store_true")
    b.set_defaults(func=cmd_backup)

    rep = sub.add_parser("report", help="Markdown-отчёт по сети")
    rep.set_defaults(func=cmd_report)

    n = sub.add_parser("notify", help="уведомление на телефон")
    n.add_argument("--title", default="Домовой")
    n.add_argument("--message", required=True)
    n.set_defaults(func=cmd_notify)

    return p


def main() -> None:
    load_secrets()
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
