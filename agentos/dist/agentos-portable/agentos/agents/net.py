"""Сетевые мини-агенты: только 192.168.1.0/24 и локальный хост."""
from __future__ import annotations

import ipaddress
import itertools
import json
import os
import re
import socket
import struct
import time
from pathlib import Path

from ..core import HOMELAB_DIR, Context, agent
from ..tools import (ToolError, homelab, http_fetch, is_local_host, resolve,
                     run_cmd, tcp_check)
from ..utils import kv, table


_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def _router_host(ctx: Context) -> str:
    try:
        inv = json.loads((HOMELAB_DIR / "homelab.json").read_text("utf-8"))
        return (inv.get("router") or {}).get("host") or "192.168.1.1"
    except (OSError, ValueError):
        return "192.168.1.1"


def _host(ctx: Context, text: str, default: str = "") -> str:
    """Достаёт хост из фразы: IP, имя с точкой или слово «роутер»."""
    m = _IPV4.search(text or "")
    if m:
        return m.group()
    for tok in (text or "").split():
        t = tok.strip(",;:()").lower()
        if t in ("роутер", "router", "шлюз", "gateway", "gw"):
            return _router_host(ctx)
        if t.count(".") >= 1 and not t.endswith(".") and "=" not in t:
            if re.fullmatch(r"[\w\-]+(?:\.[\w\-]+)+", t):
                return t
    return default


def _target(ctx: Context, text: str, default_port: int = 80) -> tuple[str, int]:
    m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})", text or "")
    if m:
        return m.group(1), int(m.group(2))
    host = _host(ctx, text)
    if not host:
        raise ValueError("укажи хост, например 192.168.1.1:80")
    mport = re.search(r":(\d{1,5})\b", text or "")
    return host, int(mport.group(1)) if mport else default_port


def _guard(ctx: Context, host: str) -> None:
    if not is_local_host(host, ctx.network):
        raise ValueError(f"{host} вне локальной сети {ctx.network}")


@agent("net.ping", "Проверка доступности", "network",
       "Быстрая проверка хоста в локальной сети: ICMP и TCP-порт",
       keywords=("пинг", "ping", "доступен", "отвечает", "живой", "проверь хост"),
       examples=("192.168.1.1:80",), needs=("net",))
def ping(ctx: Context, text: str):
    host, port = _target(ctx, text, 80)
    _guard(ctx, host)
    tcp = tcp_check(host, port)
    if os.name == "nt":                  # Windows: другие ключи ping
        icmp = run_cmd(ctx, ["ping", "-n", "1", "-w", "1000", host], timeout=5)
    else:
        icmp = run_cmd(ctx, ["ping", "-c", "1", "-W", "1", host], timeout=5)
    lines = [
        f"Хост: {host}",
        f"ICMP: {'OK' if icmp['ok'] else 'нет ответа'}",
        f"TCP {port}: {'открыт' if tcp['open'] else 'закрыт/фильтр'}",
    ]
    if icmp["ok"]:
        rtt = [l for l in icmp["out"].splitlines() if re.search(r"time[=<]", l)]
        if rtt:
            lines.append(rtt[-1].strip())
    return "\n".join(lines)


@agent("net.ports", "Проверка портов", "network",
       "Проверяет список TCP-портов на одном хосте локальной сети",
       keywords=("порты", "port", "сканируй порты", "открытые порты", "сервис"),
       examples=("192.168.1.1 22,80,443",), needs=("net",))
def ports(ctx: Context, text: str):
    host = _host(ctx, text)
    if not host:
        raise ValueError("укажи хост: 192.168.1.1 22,80")
    _guard(ctx, host)
    plist = []
    tail = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b", " ", text)
    for chunk in re.findall(r"[\d,\-]+", tail):
            chunk = chunk.strip(",")
            if not chunk:
                continue
            if "-" in chunk:
                a, b = chunk.split("-")
                plist.extend(range(int(a), int(b) + 1))
            elif chunk.isdigit():
                plist.append(int(chunk))
    plist = plist or [22, 23, 53, 80, 443, 554, 5555, 8080]
    rows = []
    for p in plist[:64]:
        r = tcp_check(host, p, timeout=0.5)
        rows.append([p, "открыт" if r["open"] else "-"])
    return f"{host}: проверено {len(rows)} портов\n" + table(
        rows, ["порт", "статус"])


@agent("net.arp", "ARP-таблица", "network",
       "Показывает соседей из ARP-кэша — кто реально в сети прямо сейчас",
       keywords=("arp", "соседи", "кто в сети", "mac", "таблица arp"),
       examples=("",), needs=("net",))
def arp(ctx: Context, text: str):
    rows = []
    try:
        lines = Path("/proc/net/arp").read_text().splitlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 6 and parts[0].count(".") == 3:
                flags = int(parts[2], 16) if parts[2].startswith("0x") else 0
                rows.append([parts[0], parts[3], "да" if flags & 2 else "нет", parts[5]])
    except OSError:
        res = run_cmd(ctx, ["ip", "neigh", "show"], timeout=5)
        if res["ok"]:
            for line in res["out"].splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "dev":
                    mac = parts[4] if len(parts) > 4 and parts[3] == "lladdr" else "?"
                    rows.append([parts[0], mac, parts[-1], parts[2]])
        else:
            inv = homelab(ctx, ["inventory"], timeout=60)
            return ("ARP-кэш недоступен (нет ip/прав на /proc). "
                    "Известные устройства по данным homelab:\n"
                    + (inv["out"].strip() if inv["ok"] and inv["out"].strip()
                       else "инвентарь пуст — запусти: homelab.py scan"))
    if not rows:
        return "ARP-кэш пуст — сеть не активна?"
    return table(rows, ["ip", "mac", "подтверждён", "интерфейс"])


@agent("net.iface", "Интерфейсы", "network",
       "Список сетевых интерфейсов, адресов и маршрут по умолчанию",
       keywords=("интерфейс", "iface", "адрес", "ip", "шлюз", "сеть"),
       examples=("",), needs=("net",))
def iface(ctx: Context, text: str):
    addr = run_cmd(ctx, ["ip", "-brief", "addr"], timeout=5)
    route = run_cmd(ctx, ["ip", "route", "show", "default"], timeout=5)
    if not addr["ok"]:
        # нет `ip` (частая ситуация в минимальных образах) — берём факты из socket
        local, host = "?", socket.gethostname()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.settimeout(0.5)
            sock.connect((ctx.cfg.get("gateway", "192.168.1.1"), 80))
            local = sock.getsockname()[0]
        except OSError:
            pass
        finally:
            sock.close()
        return kv([("хост", host), ("адрес этого хоста", local),
                   ("сеть в конфиге", ctx.network),
                   ("команда ip", "недоступна"),
                   ("пояснение", "полный список интерфейсов требует пакета iproute2")])
    return (f"Интерфейсы ({ctx.network}):\n{addr['out']}\n\n"
            f"Маршрут по умолчанию:\n{route['out'] or '(нет)'}")


@agent("net.dns", "DNS-резолв", "network",
       "Прямое и обратное разрешение имени: проверка локального DNS",
       keywords=("dns", "резолв", "имя", "ip адрес", "nslookup", "разреши"),
       examples=("192.168.1.1",), needs=("net",))
def dns(ctx: Context, text: str):
    host = _host(ctx, text)
    if not host:
        raise ValueError("укажи имя или IP")
    _guard(ctx, host)
    fwd = resolve(host)
    rev = []
    try:
        rev = [socket.gethostbyaddr(host)[0]]
    except (socket.herror, OSError):
        pass
    pairs = [("запрос", host), ("адреса", ", ".join(fwd) or "не resolved")]
    if rev:
        pairs.append(("PTR", ", ".join(rev)))
    pairs.append(("локальный", "да" if is_local_host(host, ctx.network) else "нет"))
    return kv(pairs)


@agent("net.route", "Маршруты", "network",
       "Таблица маршрутизации и проверка пути до адреса",
       keywords=("маршрут", "route", "таблица", "шлюз", "трафик"),
       examples=("",), needs=("net",))
def route(ctx: Context, text: str):
    allr = run_cmd(ctx, ["ip", "route", "show"], timeout=5)
    if not allr["ok"]:
        return f"не удалось: {allr['err']}"
    return f"Маршруты:\n{allr['out'] or '(пусто)'}"


@agent("net.scan", "Скан сети", "network",
       "Полный скан 192.168.1.0/24 через homelab.py (сохраняет state/scan.json)",
       keywords=("скан", "scan", "найди устройства", "обход сети", "кто онлайн"),
       examples=("",), needs=("net", "homelab"), tags=("slow",))
def scan(ctx: Context, text: str):
    if ctx.dry_run:
        return ("dry-run: будет выполнен `homelab.py scan` (192.168.1.0/24 → state/scan.json).\n"
                "Запуск: agentos run net.scan \"\" --live")
    from ..tools import homelab
    r = homelab(ctx, ["scan"], timeout=300)
    return (r["out"] or r["err"] or "скан завершён")[:6000]


@agent("net.inventory", "Инвентарь", "network",
       "Известные и незнакомые устройства по данным homelab.py inventory",
       keywords=("инвентарь", "inventory", "устройства", "список устройств", "незнакомые"),
       examples=("",), needs=("homelab",))
def inventory(ctx: Context, text: str):
    from ..tools import homelab
    r = homelab(ctx, ["inventory"], timeout=120)
    return (r["out"] or r["err"] or "пусто")[:6000]


@agent("net.doctor", "Диагностика", "network",
       "Полная проверка доступности: шлюз, роутер, HA, TV, мост телефона",
       keywords=("доктор", "doctor", "диагностика", "что не работает", "проверь всё"),
       examples=("",), needs=("homelab", "net"), tags=("slow",))
def doctor(ctx: Context, text: str):
    from ..tools import homelab
    r = homelab(ctx, ["doctor"], timeout=180)
    return (r["out"] or r["err"] or "пусто")[:6000]


@agent("net.httpping", "HTTP-проверка", "network",
       "HTTP-статус и заголовки локального веб-интерфейса",
       keywords=("http", "веб", "вебморда", "luci", "статус сайта", "ответ"),
       examples=("192.168.1.1",), needs=("net",))
def httpping(ctx: Context, text: str):
    host = _host(ctx, text, _router_host(ctx))
    url = host
    if "://" not in url:
        url = f"http://{url}"
    r = http_fetch(ctx, url, method="GET", timeout=4)
    if not r.get("status"):
        return f"{url} — нет ответа ({r.get('error', 'timeout')})"
    hdrs = r.get("headers", {})
    pair = [("url", url), ("статус", r["status"]),
            ("server", hdrs.get("Server", "-")),
            ("размер", f"{len(r.get('body', ''))} байт")]
    return kv(pair)


@agent("net.split", "Деление подсети", "network",
       "Делит подсеть на более мелкие: маска, диапазон, broadcast",
       keywords=("подсеть", "subnet", "маска", "разбей", "cidr", "диапазон"),
       examples=("192.168.1.0/24 /26",), needs=("net",))
def split(ctx: Context, text: str):
    words = text.split()
    net = ipaddress.ip_network(words[0], strict=False)
    prefix = 26
    if len(words) > 1 and words[1].startswith("/"):
        prefix = int(words[1][1:])
    if prefix <= net.prefixlen:
        raise ValueError(f"новая маска /{prefix} должна быть больше /{net.prefixlen}")
    total = 2 ** (prefix - net.prefixlen)
    subs = itertools.islice(net.subnets(new_prefix=prefix), 64)
    rows = [[str(s), str(s.network_address), str(s.broadcast_address),
             s.num_addresses - 2] for s in subs]
    return (f"{net} → /{prefix}: {total} подсетей"
            + (" (показаны первые 64)" if total > 64 else "")
            + "\n" + table(rows, ["сеть", "начало", "конец", "хостов"],
                           align_right={3}))


@agent("net.hostname", "Имя по IP", "network",
       "Обратное разрешение адреса и определение принадлежности к LAN",
       keywords=("hostname", "имя", "ptr", "кто такой ip", "обратный"),
       examples=("192.168.1.1",), needs=("net",))
def hostname(ctx: Context, text: str):
    ip = _host(ctx, text)
    if not ip:
        raise ValueError("укажи IP")
    _guard(ctx, ip)
    try:
        name = socket.gethostbyaddr(ip)[0]
    except (socket.herror, OSError):
        name = None
    return kv([("ip", ip), ("имя", name or "не найдено"),
               ("в LAN", "да" if is_local_host(ip, ctx.network) else "нет")])


@agent("net.wol", "Wake-on-LAN", "network",
       "Будит устройство magic-пакетом (по умолчанию только показывает план)",
       keywords=("wol", "wake", "разбуди", "включи по сети", "magic packet"),
       examples=("aa:bb:cc:dd:ee:ff",), needs=("net",), tags=("write",))
def wol(ctx: Context, text: str):
    mac = (text.split() or [""])[0].replace("-", ":").lower()
    if len(mac.split(":")) != 6:
        raise ValueError("нужен MAC вида aa:bb:cc:dd:ee:ff")
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    packet = b"\xff" * 6 + mac_bytes * 16
    if ctx.dry_run:
        return (f"dry-run: magic-пакет для {mac} на 192.168.1.255:9 "
                f"({len(packet)} байт). Запуск с --live.")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(packet, ("192.168.1.255", 9))
    return f"magic-пакет отправлен: {mac}"


@agent("net.usage", "Трафик интерфейсов", "network",
       "Счётчики RX/TX по интерфейсам и средняя скорость за интервал",
       keywords=("трафик", "скорость", "rx", "tx", "байты", "загрузка канала"),
       examples=("",), needs=("net",))
def usage(ctx: Context, text: str):
    def snap():
        out = {}
        try:
            raw = Path("/proc/net/dev").read_text()
        except OSError:
            return None
        for line in raw.splitlines()[2:]:
            if ":" not in line:
                continue
            name, vals = line.split(":", 1)
            f = vals.split()
            out[name.strip()] = (int(f[0]), int(f[8]))
        return out

    first = snap()
    if first is None:
        res = run_cmd(ctx, ["ip", "-s", "link"], timeout=5)
        return ("/proc/net/dev недоступен (нет прав); счётчики ip -s link:\n"
                + (res["out"] or res["err"] or "(пусто)"))
    if not ctx.dry_run:
        time.sleep(1.0)
    second = snap() or first
    rows = []
    for name, (rx, tx) in second.items():
        if name == "lo":
            continue
        r0, t0 = first.get(name, (rx, tx))
        rows.append([name, f"{rx / 1e6:.1f} МБ", f"{tx / 1e6:.1f} МБ",
                     f"{(rx - r0) / 1024:.0f} КБ/с", f"{(tx - t0) / 1024:.0f} КБ/с"])
    return table(rows, ["iface", "всего RX", "всего TX", "RX/с", "TX/с"],
                 align_right={1, 2, 3, 4})
