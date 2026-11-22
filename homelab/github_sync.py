#!/usr/bin/env python3
"""Еженедельные бэкап homelab и синхронизация навыков в приватный GitHub-репозиторий Domovoy-.

Только stdlib + git. Секреты не читаются и не публикуются.
Использование:
    python3 github_sync.py all [--dry-run]
    python3 github_sync.py skills [--dry-run]
    python3 github_sync.py backup [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/root/workspace")
HOMELAB = WORKSPACE / "homelab"
STATE_DIR = HOMELAB / "state"
REPO = HOMELAB / "github-domovoy"
DEFAULT_REMOTE = "git@github.com:sahanaservicii/Domovoy-.git"
SKILLS_SRC = Path(os.environ.get("OPENCODE_CONFIG_HOME", str(Path.home() / ".config/opencode"))) / "skills"
BACKUP_DIR = HOMELAB / "backups"
SKILLS_DST_REL = Path(".config/opencode/skills")
BACKUPS_REL = Path("backups")
STATE_FILE = STATE_DIR / "github_sync.json"

SECRET_NAME_RE = re.compile(
    r"(^|/)(secrets?|\.env[^/]*|.*(token|password|passwd|secret|private[_-]?key).*|.*\.(key|pem|p12|pfx))$",
    re.IGNORECASE,
)
KEY_MARKER = b"-----BEGIN "
SKIP_NAMES = {".git", "__pycache__", "node_modules", "dist", "build"}


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if check and p.returncode != 0:
        tail = (p.stderr or p.stdout or "").strip()[-300:]
        raise RuntimeError(f"команда {' '.join(cmd)}: rc={p.returncode}: {tail}")
    return p


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_repo(remote: str, dry_run: bool) -> Path | None:
    p = run(["git", "ls-remote", "--heads", remote], check=False)
    if p.returncode != 0:
        raise RuntimeError(f"нет доступа к {remote}: {(p.stderr or '').strip()[-200:]}")
    if dry_run:
        return None
    if not (REPO / ".git").exists():
        if REPO.exists() and any(REPO.iterdir()):
            raise RuntimeError(f"{REPO} не пустой и не git-репозиторий — не трогаю")
        run(["git", "clone", remote, str(REPO)])
    cur = run(["git", "-C", str(REPO), "remote", "get-url", "origin"], check=False).stdout.strip()
    if cur != remote:
        run(["git", "-C", str(REPO), "remote", "set-url", "origin", remote])
    run(["git", "-C", str(REPO), "config", "user.name", "Domovoy"])
    run(["git", "-C", str(REPO), "config", "user.email", "domovoy@localhost"])
    heads = run(["git", "ls-remote", "--heads", remote, "refs/heads/main"]).stdout.strip()
    if heads:
        run(["git", "-C", str(REPO), "fetch", "origin", "main"], check=False)
        run(["git", "-C", str(REPO), "pull", "--ff-only", "origin", "main"], check=False)
    return REPO


def copy_skills(repo: Path) -> int:
    if not SKILLS_SRC.is_dir():
        raise RuntimeError(f"нет каталога навыков {SKILLS_SRC}")
    dst = repo / SKILLS_DST_REL
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for child in sorted(SKILLS_SRC.iterdir()):
        if not child.is_dir() or child.name in SKIP_NAMES or not (child / "SKILL.md").is_file():
            continue
        target = dst / child.name
        if target.exists():
            shutil.rmtree(target)  # только внутри нашего рабочего клона
        shutil.copytree(
            child,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "*.env", "*token*", "*password*", "*.key", "*.pem"),
        )
        count += 1
    readme = repo / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Domovoy — навыки и еженедельные бэкапы\n\n"
            "Приватный репозиторий. Синхронизация выполняется скриптом "
            "`homelab/github_sync.py` еженедельно.\n\n"
            "- `.config/opencode/skills/` — все локальные навыки Домового.\n"
            "- `backups/` — локальные бэкапы homelab (инвентарь, scan.json).\n\n"
            "Секреты, ключи и токены сюда не попадают.\n",
            encoding="utf-8",
        )
    gitignore = repo / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "**/secrets/**\n*.env\n*.env.*\n!.env.example\n*.key\n*.pem\n*.p12\n*.pfx\n"
            "*token*\n*password*\n__pycache__/\n*.pyc\n",
            encoding="utf-8",
        )
    return count


def secret_guard(repo: Path, roots: list[Path]) -> None:
    for root in roots:
        base = repo / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            rel = path.relative_to(repo).as_posix()
            if ".git/" in rel or "/.git" in rel:
                continue
            if not path.is_file():
                continue
            if SECRET_NAME_RE.search(rel):
                raise RuntimeError(f"похоже на секрет, публикация прервана: {rel}")
            try:
                if KEY_MARKER in path.read_bytes():
                    raise RuntimeError(f"найден приватный ключ, публикация прервана: {rel}")
            except OSError:
                continue


def commit_push(repo: Path, paths: list[str], message: str) -> str:
    run(["git", "-C", str(repo), "add", "--"] + paths)
    if run(["git", "-C", str(repo), "diff", "--cached", "--quiet"], check=False).returncode == 0:
        return "нет изменений"
    secret_guard(repo, [Path(p) for p in paths if p != "backups"])
    run(["git", "-C", str(repo), "commit", "-m", message])
    run(["git", "-C", str(repo), "push", "origin", "HEAD:refs/heads/main"])
    sha = run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"]).stdout.strip()
    return f"опубликовано {sha}"


def do_skills(remote: str, dry_run: bool) -> dict:
    repo = ensure_repo(remote, dry_run)
    local = [p.name for p in SKILLS_SRC.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()] if SKILLS_SRC.is_dir() else []
    if dry_run:
        return {"ok": True, "dry_run": True, "skills_local": len(local), "plan": "копировать навыки в .config/opencode/skills/ и запушить в main (без commit/push)"}
    if not repo:
        raise RuntimeError("ensure_repo не вернул путь")
    count = copy_skills(repo)
    result = commit_push(repo, [".config/opencode/skills", "README.md", ".gitignore"], f"chore: sync skills {datetime.now():%Y-%m-%d}")
    return {"ok": True, "skills_local": len(local), "skills_copied": count, "result": result}


def do_backup(remote: str, dry_run: bool) -> dict:
    repo = ensure_repo(remote, dry_run)
    latest = max(BACKUP_DIR.glob("homelab-*.tar.gz"), key=lambda p: p.stat().st_mtime, default=None) if BACKUP_DIR.exists() else None
    if dry_run:
        return {"ok": True, "dry_run": True, "latest_local": latest.name if latest else None, "plan": "создать homelab.py backup и запушить архив + манифест в backups/ (без commit/push)"}
    if not repo:
        raise RuntimeError("ensure_repo не вернул путь")
    run([sys.executable, str(HOMELAB / "homelab.py"), "backup"], cwd=HOMELAB)
    latest = max(BACKUP_DIR.glob("homelab-*.tar.gz"), key=lambda p: p.stat().st_mtime, default=None)
    if not latest:
        raise RuntimeError("архив бэкапа не создан")
    stamp = latest.name[len("homelab-"):-len(".tar.gz")]
    manifest = BACKUP_DIR / f"homelab-{stamp}.json"
    dest_dir = repo / BACKUPS_REL / datetime.now().strftime("%Y/%m")
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest, dest_dir / latest.name)
    if manifest.exists():
        shutil.copy2(manifest, dest_dir / manifest.name)
    result = commit_push(repo, ["backups"], f"chore: weekly backup {datetime.now():%Y-%m-%d}")
    return {"ok": True, "archive": latest.name, "result": result}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["all", "skills", "backup"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--remote", default=DEFAULT_REMOTE)
    args = ap.parse_args()

    results: dict[str, dict] = {}
    for name, func in (("skills", do_skills), ("backup", do_backup)):
        if args.mode not in ("all", name):
            continue
        try:
            results[name] = func(args.remote, args.dry_run)
        except Exception as exc:  # noqa: BLE001
            results[name] = {"ok": False, "error": str(exc)[:300]}

    ok = all(v.get("ok") for v in results.values())
    payload = {"last_run_utc": utc_now(), "mode": args.mode, "ok": ok, "results": results}
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
