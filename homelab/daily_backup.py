#!/usr/bin/env python3
"""Ежедневный бэкап: локальный конфиг + роутер + HA (через SSH-туннель при необходимости).

Запуск: python3 /root/workspace/homelab/daily_backup.py
Результат: архивы в backups/ + отчёт в state/daily_backup.json.
Секреты не печатаются. Ничего не удаляется.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
BACKUP_DIR = ROOT / "backups"
STATE_DIR = ROOT / "state"
TUNNEL_PORT = 18123
HA_LAN = "192.168.1.156"
HA_URL_LAN = f"http://{HA_LAN}:8123"
HA_URL_TUNNEL = f"http://127.0.0.1:{TUNNEL_PORT}"
TUNNEL_LOG = Path("/tmp/opencode/daily_backup_tunnel.log")


def tcp_open(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def load_token():
    secret = Path(os.environ.get(
        "OPENCODE_CONFIG_HOME", str(Path.home() / ".config" / "opencode")
    )) / "secrets" / "homelab.env"
    if not secret.exists():
        return ""
    for line in secret.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("HASS_TOKEN="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def start_tunnel():
    """Поднять SSH-туннель 127.0.0.1:18123 -> HA:8123 через роутер."""
    if tcp_open("127.0.0.1", TUNNEL_PORT, 1):
        return True, "уже поднят"
    key = Path.home() / ".ssh" / "id_ed25519"
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
        "-o", "StrictHostKeyChecking=accept-new", "-o", "ExitOnForwardFailure=yes",
        "-N", "-L", f"{TUNNEL_PORT}:{HA_LAN}:8123",
        "-p", "22", "-i", str(key), "root@sahanovschi.v6.rocks",
    ]
    TUNNEL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(TUNNEL_LOG, "ab") as log:
        subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
    for _ in range(12):
        time.sleep(1)
        if tcp_open("127.0.0.1", TUNNEL_PORT, 1):
            return True, "поднят через роутер"
    return False, "не удалось поднять"


def ha_config(ha_url, token):
    req = urllib.request.Request(
        ha_url + "/api/config", headers={"Authorization": "Bearer " + token}
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report = {
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "stamp": stamp, "local": None, "router": None, "ha": None,
        "cloud": "не настроен", "errors": [],
    }

    # 1) Локальный конфиг + роутер через штатную команду
    try:
        p = subprocess.run(
            [sys.executable, str(ROOT / "homelab.py"), "backup", "--with-router"],
            capture_output=True, text=True, timeout=150, cwd=str(ROOT),
        )
        for line in (p.stdout + "\n" + p.stderr).splitlines():
            if "Локальный бэкап:" in line:
                report["local"] = line.split(":", 1)[1].strip().split(" ")[0]
            if "Бэкап роутера:" in line:
                report["router"] = line.split(":", 1)[1].strip()
        if report["local"] is None:
            report["errors"].append("локальный бэкап: " + (p.stderr or p.stdout)[:200])
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"backup --with-router: {exc}"[:200])

    # 2) HA: прямо в LAN, иначе через туннель
    token = load_token()
    if not token:
        report["errors"].append("нет HASS_TOKEN")
    else:
        url, via = HA_URL_LAN, "LAN"
        if not tcp_open(HA_LAN, 8123, 2):
            ok, how = start_tunnel()
            if ok:
                url, via = HA_URL_TUNNEL, "туннель (" + how + ")"
            else:
                report["errors"].append("HA недоступен, туннель: " + how)
        if url and token:
            try:
                cfg = ha_config(url, token)
                hb = BACKUP_DIR / f"ha-config-{stamp}.json"
                hb.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
                report["ha"] = {"file": hb.name, "via": via, "version": cfg.get("version")}
            except Exception as exc:  # noqa: BLE001
                report["errors"].append(f"HA config ({via}): {exc}"[:200])

    out = STATE_DIR / "daily_backup.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
