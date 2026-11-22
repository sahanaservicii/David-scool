#!/usr/bin/env python3
"""Включение GitHub Pages для репозитория Family-Sahanovsci через локальный токен.

Токен НЕ печатается и НЕ передаётся в аргументах: только читается из
/root/.config/opencode/secrets/homelab.env по имени переменной.

Использование:
    python3 github_pages_enable.py GITHUB_TOKEN
    python3 github_pages_enable.py GITHUB_TOKEN --check
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

SECRETS = Path("/root/.config/opencode/secrets/homelab.env")
REPO = "sahanaservicii/Family-Sahanovsci"
API = f"https://api.github.com/repos/{REPO}/pages"


def read_token(name: str) -> str:
    if not SECRETS.is_file():
        raise RuntimeError(f"нет файла секретов {SECRETS}")
    for line in SECRETS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            token = value.strip().strip("\"'")
            if not token:
                raise RuntimeError(f"переменная {name} пуста")
            return token
    raise RuntimeError(f"в {SECRETS} нет переменной {name}")


def request(method: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        API,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"http": r.status, "body": json.loads(r.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(body)
        except ValueError:
            pass
        return {"http": e.code, "body": body}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("token_var", help="имя переменной с токеном в secrets/homelab.env")
    ap.add_argument("--check", action="store_true", help="только прочитать текущий статус Pages")
    args = ap.parse_args()
    try:
        token = read_token(args.token_var)
        result = request("GET", token) if args.check else request(
            "PUT", token, {"source": {"branch": "main", "path": "/"}}
        )
        out = {
            "http": result["http"],
            "status": result["body"].get("status") if isinstance(result["body"], dict) else None,
            "source": result["body"].get("source") if isinstance(result["body"], dict) else None,
            "url": "https://sahanaservicii.github.io/Family-Sahanovsci/",
        }
        if isinstance(result["body"], dict) and "message" in result["body"]:
            out["message"] = result["body"]["message"]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if result["http"] in (200, 201, 204) else 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)[:300]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
