#!/usr/bin/env python3
"""Безопасная смена активного Xray-конфига на роутере OpenWrt.

Только локальный SSH. Секреты не печатаются. Без флага --apply ничего не меняет.
Рабочий файл должен уже лежать НА РОУТЕРЕ (например, /root/new-xray-config.json).
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
INVENTORY = SCRIPT_DIR / "homelab.json"


def router_info() -> dict:
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    return data["locations"]["dacha"]["router"]


def remote(command: str, timeout: int = 45) -> tuple:
    info = router_info()
    key = os.environ.get("HOMELAB_SSH_KEY") or info.get("identity")
    host = info["host"]
    user = info.get("user", "root")
    port = int(info.get("port", 22))
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
        "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
        "-p", str(port),
    ]
    if key:
        cmd += ["-i", os.path.expanduser(key)]
    cmd += [f"{user}@{host}", command]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, (result.stdout + result.stderr).strip()


def show_status() -> None:
    rc, out = remote(
        "echo '### HC'; tail -2 /tmp/xray-hc.log 2>/dev/null; "
        "echo '### NFT'; nft list table inet xrayredir 2>/dev/null | wc -l; "
        "echo '### YT_SOCKS'; curl -sS -m 8 --socks5-hostname 127.0.0.1:10808 "
        "-o /dev/null -w '%{http_code}' https://www.youtube.com/ 2>/dev/null; echo; "
        "echo '### TEST_PROCS'; ps w 2>/dev/null | grep -c '[x]ray run -c /etc/xray/test.json'"
    )
    print(out or "(нет ответа)")
    if rc != 0:
        print(f"SSH код: {rc}", file=sys.stderr)


def apply_config(path: str) -> int:
    q = shlex.quote(path)
    rc, out = remote(f"test -r {q} && echo READABLE")
    if rc != 0 or "READABLE" not in out:
        print(f"ОШИБКА: файл недоступен на роутере: {path}")
        return 1

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = f"/etc/xray/config.json.bak-{stamp}"
    rc, out = remote(f"cp /etc/xray/config.json {backup} && echo BACKUP_OK")
    if rc != 0 or "BACKUP_OK" not in out:
        print("ОШИБКА: не удалось сделать бэкап текущего конфига")
        return 1
    print(f"Бэкап на роутере: {backup}")

    rc, out = remote(f"/etc/xray/xray run -c {q} -test")
    if rc != 0:
        print("ОШИБКА: новый конфиг не прошёл xray -test:")
        print("\n".join(out.splitlines()[-5:]))
        return 1

    rc, out = remote(
        f"cp {q} /etc/xray/config.json && chmod 600 /etc/xray/config.json && "
        "/etc/xray/xray run -c /etc/xray/config.json -test"
    )
    if rc != 0:
        print("ОШИБКА: конфиг не прошёл проверку после копирования, откатываю")
        remote(f"cp {backup} /etc/xray/config.json && /etc/init.d/xray restart")
        print("\n".join(out.splitlines()[-5:]))
        return 1

    remote("/etc/init.d/xray restart")
    print("Xray перезапущен, жду проверку...")
    time.sleep(6)
    rc, out = remote(
        "echo '### HC'; tail -2 /tmp/xray-hc.log 2>/dev/null; "
        "echo '### NFT'; nft list table inet xrayredir 2>/dev/null | wc -l; "
        "echo '### YT'; curl -sS -m 8 --socks5-hostname 127.0.0.1:10808 "
        "-o /dev/null -w '%{http_code}' https://www.youtube.com/ 2>/dev/null; echo"
    )
    print(out or "(нет ответа)")
    if "### YT" in out:
        lines = out.splitlines()
        yt = lines[-1].strip() if lines else ""
        if yt in ("200", "301", "302", "307", "308"):
            print("РЕЗУЛЬТАТ: YouTube доступен через новый конфиг")
            return 0

    print("РЕЗУЛЬТАТ: проверка не прошла, откатываю конфиг")
    remote(f"cp {backup} /etc/xray/config.json && /etc/init.d/xray restart")
    print(f"Восстановлено из {backup}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", metavar="PATH_ON_ROUTER",
                        help="путь к готовому config.json на роутере")
    parser.add_argument("--check", action="store_true",
                        help="только показать статус (по умолчанию)")
    args = parser.parse_args()

    if args.apply:
        return apply_config(args.apply)
    show_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
