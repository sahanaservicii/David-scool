#!/usr/bin/env python3
"""
Помощник цикла самоулучшения Домового (stdlib only, offline).
Использование:
  python3 cycle.py status
  python3 cycle.py resource-check
  python3 cycle.py log --status success|failure|skipped --summary "..." [--backup "..."]
  python3 cycle.py backup-homelab [--with-router] [--with-ha]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATE = BASE / "state.json"
HOMELAB = BASE.parent / "homelab.py"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"enabled": True, "runs": 0, "successes": 0, "failures": 0}


def save_state(data: dict) -> None:
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_status(_: argparse.Namespace) -> int:
    data = load_state()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_resource_check(_: argparse.Namespace) -> int:
    info = {"ok": True, "notes": []}
    try:
        load1, _, _ = os.getloadavg()
        cpu = os.cpu_count() or 1
        info["load1"] = round(load1, 2)
        info["cpu"] = cpu
        if load1 > max(2.0, cpu * 1.5):
            info["ok"] = False
            info["notes"].append("высокая нагрузка")
    except Exception:
        info["notes"].append("loadavg недоступен")
    # /proc/meminfo if available
    try:
        mem = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                k, _, v = line.partition(":")
                if k in ("MemAvailable", "MemTotal", "SwapFree", "SwapTotal"):
                    mem[k] = int(v.strip().split()[0])
        if mem:
            info["mem_kb"] = mem
            avail = mem.get("MemAvailable", 0)
            total = mem.get("MemTotal", 1)
            if total and avail / total < 0.08:
                info["ok"] = False
                info["notes"].append("мало доступной памяти")
    except Exception:
        info["notes"].append("meminfo недоступен")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info["ok"] else 2


def cmd_log(args: argparse.Namespace) -> int:
    data = load_state()
    ts = now_utc()
    data["last_run_utc"] = ts
    data["last_status"] = args.status
    data["last_summary"] = args.summary
    data["runs"] = int(data.get("runs", 0)) + 1
    if args.backup:
        data["last_backup"] = args.backup
    if args.status == "success":
        data["last_success_utc"] = ts
        data["successes"] = int(data.get("successes", 0)) + 1
    elif args.status == "failure":
        data["failures"] = int(data.get("failures", 0)) + 1
    save_state(data)
    print(json.dumps({"ok": True, "state": data}, ensure_ascii=False, indent=2))
    return 0


def cmd_backup_homelab(args: argparse.Namespace) -> int:
    cmd = [sys.executable, str(HOMELAB), "backup"]
    if args.with_router:
        cmd.append("--with-router")
    if args.with_ha:
        cmd.append("--with-ha")
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    print(out.strip())
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("resource-check")
    p.set_defaults(func=cmd_resource_check)

    p = sub.add_parser("log")
    p.add_argument("--status", choices=["success", "failure", "skipped"], required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--backup")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("backup-homelab")
    p.add_argument("--with-router", action="store_true")
    p.add_argument("--with-ha", action="store_true")
    p.set_defaults(func=cmd_backup_homelab)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
