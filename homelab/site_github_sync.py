#!/usr/bin/env python3
"""Публикация только статического сайта family-site в GitHub (без ключей и бэкапов).

Только stdlib + git, доступ по уже настроенному SSH-ключу. Роутер/HA не трогаются.

Команды:
    init                  подготовить git-репозиторий сайта, remote, hook автопуша
    sync [--message ...]  коммит изменений и пуш; при недоступности GitHub — локальный коммит
    push                  только пуш текущего HEAD (используется хуком)
    status                текущее состояние репозитория и последнего пуша
    check                 проверка файлов сайта на похожие на секреты (без изменений)

Пример: python3 /root/workspace/homelab/site_github_sync.py sync --message "site: update"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SITE = Path("/root/workspace/family-site")
DEFAULT_REMOTE = "git@github.com:sahanaservicii/Family-Sahanovsci.git"
STATE_DIR = Path("/root/workspace/homelab/state")
STATE_FILE = STATE_DIR / "site_github_sync.json"
LOG_FILE = STATE_DIR / "site_github_push.log"

SECRET_NAME_RE = re.compile(
    r"(^|/)(secrets?|\.env[^/]*|.*(token|password|passwd|secret|private[_-]?key).*|.*\.(key|pem|p12|pfx))$",
    re.IGNORECASE,
)
KEY_MARKER = b"-----BEGIN "
HOOK = """#!/usr/bin/env bash
# Автопуш после каждого коммита. При недоступности GitHub коммит остаётся локально.
if [ "${SITE_SYNC_SKIP_HOOK:-}" = "1" ]; then exit 0; fi
python3 /root/workspace/homelab/site_github_sync.py push >> \\
  /root/workspace/homelab/state/site_github_push.log 2>&1 || true
exit 0
"""


def run(cmd: list[str], check: bool = True, timeout: int = 60, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd or SITE), text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "таймаут")
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: rc={p.returncode}: {(p.stderr or p.stdout).strip()[-300:]}")
    return p


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_state(payload: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def log(line: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{now()} {line}\n")


def secret_check() -> list[str]:
    """Вернуть список подозрительных файлов. Ничего не печатает их содержимое."""
    found: list[str] = []
    for path in sorted(SITE.rglob("*")):
        rel = path.relative_to(SITE).as_posix()
        if rel == ".git" or rel.startswith(".git/") or rel.startswith("state/"):
            continue
        if not path.is_file():
            continue
        if SECRET_NAME_RE.search(rel):
            found.append(rel)
            continue
        try:
            if KEY_MARKER in path.read_bytes():
                found.append(rel)
        except OSError:
            continue
    return found


def do_check() -> dict:
    bad = secret_check()
    files = [p.relative_to(SITE).as_posix() for p in sorted(SITE.rglob("*"))
             if p.is_file() and not p.relative_to(SITE).as_posix().startswith(".git/")]
    return {"ok": not bad, "files": files, "suspicious": bad}


def ensure_repo(remote: str) -> None:
    gitdir = SITE / ".git"
    if not gitdir.exists():
        run(["git", "init", "-b", "main", str(SITE)], cwd=Path("/root/workspace"))
    run(["git", "-C", str(SITE), "config", "user.name", "Domovoy"])
    run(["git", "-C", str(SITE), "config", "user.email", "domovoy@localhost"])
    current = run(["git", "-C", str(SITE), "remote", "get-url", "origin"], check=False).stdout.strip()
    if not current:
        run(["git", "-C", str(SITE), "remote", "add", "origin", remote])
    elif current != remote:
        run(["git", "-C", str(SITE), "remote", "set-url", "origin", remote])
    branch = run(["git", "-C", str(SITE), "rev-parse", "--abbrev-ref", "HEAD"], check=False).stdout.strip()
    if branch and branch != "main":
        run(["git", "-C", str(SITE), "branch", "-M", "main"])


def install_hook() -> None:
    hook_path = SITE / ".git" / "hooks" / "post-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(HOOK, encoding="utf-8")
    hook_path.chmod(0o755)


def push_head() -> dict:
    sha = run(["git", "-C", str(SITE), "rev-parse", "--short", "HEAD"]).stdout.strip()
    p = run(["git", "-C", str(SITE), "push", "origin", "HEAD:refs/heads/main"], check=False, timeout=90)
    if p.returncode == 0:
        state = {"ok": True, "status": "pushed", "sha": sha, "at": now(), "error": ""}
        log(f"PUSH OK {sha}")
    else:
        err = (p.stderr or p.stdout or "").strip().splitlines()
        state = {"ok": False, "status": "local_only", "sha": sha, "at": now(),
                 "error": (err[-1] if err else f"rc={p.returncode}")[:300]}
        log(f"PUSH FAIL {sha}: {state['error']}")
    write_state(state)
    return state


def do_init(remote: str) -> dict:
    check = do_check()
    if not check["ok"]:
        raise RuntimeError("в файлах сайта найдены похожие на секреты данные: " + ", ".join(check["suspicious"]))
    ensure_repo(remote)
    install_hook()
    return {"ok": True, "site": str(SITE), "remote": remote, "branch": "main",
            "files": len(check["files"]), "hook": "post-commit установлен"}


def do_sync(remote: str, message: str) -> dict:
    ensure_repo(remote)
    bad = secret_check()
    if bad:
        raise RuntimeError("публикация прервана, подозрительные файлы: " + ", ".join(bad))
    run(["git", "-C", str(SITE), "add", "--all"])
    if run(["git", "-C", str(SITE), "diff", "--cached", "--quiet"], check=False).returncode == 0:
        return {"ok": True, "status": "no_changes", "at": now()}
    old = os.environ.get("SITE_SYNC_SKIP_HOOK")
    os.environ["SITE_SYNC_SKIP_HOOK"] = "1"
    try:
        run(["git", "-C", str(SITE), "commit", "-m", message])
    finally:
        if old is None:
            os.environ.pop("SITE_SYNC_SKIP_HOOK", None)
        else:
            os.environ["SITE_SYNC_SKIP_HOOK"] = old
    result = push_head()
    return {"ok": result["ok"], "status": result["status"], "sha": result["sha"],
            "message": message, "error": result["error"], "at": result["at"]}


def do_status() -> dict:
    state = read_state()
    head = run(["git", "-C", str(SITE), "rev-parse", "--short", "HEAD"], check=False).stdout.strip()
    remote = run(["git", "-C", str(SITE), "remote", "get-url", "origin"], check=False).stdout.strip()
    dirty = run(["git", "-C", str(SITE), "status", "--porcelain"], check=False).stdout.strip()
    return {"head": head, "remote": remote, "dirty": bool(dirty), "last_push": state}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["init", "sync", "push", "status", "check"])
    ap.add_argument("--remote", default=DEFAULT_REMOTE)
    ap.add_argument("--message", default="site: auto-sync " + now())
    args = ap.parse_args()
    try:
        if args.command == "init":
            result = do_init(args.remote)
        elif args.command == "sync":
            result = do_sync(args.remote, args.message)
        elif args.command == "push":
            result = push_head()
        elif args.command == "check":
            result = do_check()
        else:
            result = do_status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok", True) else 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)[:400]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
