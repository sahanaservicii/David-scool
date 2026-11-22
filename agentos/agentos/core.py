"""agentos.core — ядро офлайн-мультиагентной системы.

Только стандартная библиотека Python. Никаких облаков: сеть ограничена
локальным периметром, LLM — опциональный локальный эндпоинт.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

VERSION = "1.0.0"
EXPECTED_AGENTS = 113

def _app_root() -> Path:
    """Корень приложения: env, каталог .pyz или папка проекта — что найдётся."""
    env = os.environ.get("AGENTOS_HOME")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:          # zipapp: /path/app.pyz/agentos/core.py
        if parent.suffix == ".pyz":
            return parent.parent
    return here.parent.parent


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", "utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _data_dir(name: str, env_key: str) -> Path:
    env = os.environ.get(env_key)
    if env:
        return Path(env).expanduser().resolve()
    preferred = ROOT / name
    if _writable(preferred):            # флешка/папка: данные рядом с приложением
        return preferred.resolve()
    local = os.environ.get("LOCALAPPDATA")          # Windows
    base = Path(local) if local else Path.home() / ".local" / "share"
    return (base / "agentos" / name).resolve()


def _homelab_dir() -> Path:
    env = os.environ.get("HOMELAB_DIR")
    candidates = [Path(env).expanduser()] if env else []
    candidates += [ROOT / "homelab", ROOT.parent / "homelab"]
    for candidate in candidates:
        if (candidate / "homelab.py").exists():
            return candidate.resolve()
    return (ROOT / "homelab").resolve()


ROOT = _app_root()
DATA = _data_dir("data", "AGENTOS_DATA")
OUT = _data_dir("out", "AGENTOS_OUT")
LOGS = DATA / "logs"
DB_PATH = DATA / "memory.sqlite"
CONFIG_PATH = DATA / "config.json"
HOMELAB_DIR = _homelab_dir()

DEFAULT_CONFIG: dict = {
    "version": 1,
    "network": "192.168.1.0/24",
    "safety": {
        "dry_run_default": True,
        "allow_shell": True,
        "max_read_bytes": 400_000,
        "shell_timeout": 15,
    },
    "llm": {
        "enabled": True,          # пробуем локальный эндпоинт, если он поднят
        "url": "http://127.0.0.1:8080/v1",
        "fallback_urls": ["http://127.0.0.1:11434/v1"],
        "model": "local",
        "timeout": 90,
    },
    "server": {"host": "127.0.0.1", "port": 8765, "token": ""},
    "notify": {"enabled": False},
}


# ================================================================ токенизация
_WORD_RE = re.compile(r"[0-9a-zа-я]+")
_SUFFIXES = (
    "иями", "ями", "ами", "ыми", "ими", "ов", "ев", "ий", "ый", "ая", "ое",
    "ые", "ой", "ей", "ам", "ям", "ах", "ях", "ом", "ем", "ия", "ие", "ию",
    "ть", "ся", "сь", "ы", "и", "а", "е", "о", "у", "ю", "я",
)


def _stem(word: str) -> str:
    if len(word) <= 4 or word.isdigit():
        return word
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[: -len(suf)]
    return word


def norm_tokens(text: str) -> list[str]:
    text = (text or "").lower().replace("ё", "е")
    return [_stem(w) for w in _WORD_RE.findall(text)]


# ================================================================ результат
@dataclass
class Result:
    agent: str
    ok: bool = True
    output: Any = None
    error: str | None = None
    ms: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
            "ms": self.ms,
            "notes": self.notes,
        }

    def text(self) -> str:
        if not self.ok:
            return f"[{self.agent}] ошибка: {self.error}"
        out = self.output
        if out is None:
            return f"[{self.agent}] готово (без вывода)"
        if isinstance(out, str):
            return out
        if isinstance(out, (dict, list, tuple)):
            return json.dumps(out, ensure_ascii=False, indent=2, default=str)
        return str(out)


# ================================================================ конфиг
def load_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text("utf-8"))
            _deep_update(cfg, user)
        except (OSError, ValueError):
            pass
    env_url = os.environ.get("AGENTOS_LLM_URL")
    if env_url:
        cfg["llm"]["url"] = env_url
        cfg["llm"]["enabled"] = True
    return cfg


def save_config(cfg: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


def _deep_update(base: dict, extra: dict) -> None:
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v


# ================================================================ память
class Memory:
    """SQLite: прогоны, факты, заметки, задачи. Всё локально."""

    def __init__(self, path: Path | None = None):
        DATA.mkdir(parents=True, exist_ok=True)
        self.path = Path(path or DB_PATH)
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs(
                id INTEGER PRIMARY KEY, ts TEXT, agent TEXT, ok INTEGER,
                ms INTEGER, query TEXT, output TEXT);
            CREATE TABLE IF NOT EXISTS facts(
                key TEXT PRIMARY KEY, value TEXT, tags TEXT, ts TEXT);
            CREATE TABLE IF NOT EXISTS notes(
                id INTEGER PRIMARY KEY, ts TEXT, text TEXT, tags TEXT);
            CREATE TABLE IF NOT EXISTS todos(
                id INTEGER PRIMARY KEY, ts TEXT, text TEXT, due TEXT,
                done INTEGER DEFAULT 0, done_ts TEXT);
            CREATE INDEX IF NOT EXISTS idx_runs_ts ON runs(ts);
            CREATE INDEX IF NOT EXISTS idx_notes_ts ON notes(ts);
            CREATE INDEX IF NOT EXISTS idx_todos_done ON todos(done);
            """
        )
        self.db.commit()

    # --- прогоны
    def log_run(self, agent: str, ok: bool, ms: int, query: str, output: Any) -> int:
        text = output if isinstance(output, str) else json.dumps(
            output, ensure_ascii=False, default=str)
        cur = self.db.execute(
            "INSERT INTO runs(ts, agent, ok, ms, query, output) VALUES(?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), agent, int(ok), ms,
             (query or "")[:400], (text or "")[:20000]),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def runs(self, limit: int = 20, agent: str | None = None) -> list[dict]:
        sql = "SELECT id, ts, agent, ok, ms, query, output FROM runs"
        args: list = []
        if agent:
            sql += " WHERE agent=?"
            args.append(agent)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.db.execute(sql, args)]

    def stats(self) -> dict:
        row = self.db.execute(
            "SELECT COUNT(*) n, SUM(ok) ok, AVG(ms) ms FROM runs").fetchone()
        per = self.db.execute(
            "SELECT agent, COUNT(*) n FROM runs GROUP BY agent ORDER BY n DESC LIMIT 12"
        ).fetchall()
        return {
            "runs": row["n"] or 0,
            "ok": row["ok"] or 0,
            "avg_ms": round(row["ms"] or 0, 1),
            "top": [(r["agent"], r["n"]) for r in per],
        }

    # --- факты
    def fact_set(self, key: str, value: Any, tags: str = "") -> None:
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, default=str)
        self.db.execute(
            "INSERT INTO facts(key, value, tags, ts) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "tags=excluded.tags, ts=excluded.ts",
            (key, value, tags, datetime.now().isoformat(timespec="seconds")),
        )
        self.db.commit()

    def fact_get(self, key: str):
        row = self.db.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def facts(self, like: str = "") -> list[dict]:
        sql = "SELECT * FROM facts"
        args: list = []
        if like:
            sql += " WHERE key LIKE ? OR tags LIKE ?"
            args = [f"%{like}%", f"%{like}%"]
        sql += " ORDER BY ts DESC"
        return [dict(r) for r in self.db.execute(sql, args)]

    # --- заметки
    def note_add(self, text: str, tags: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO notes(ts, text, tags) VALUES(?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), text, tags),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def notes(self, like: str = "", limit: int = 50) -> list[dict]:
        sql = "SELECT * FROM notes"
        args: list = []
        if like:
            sql += " WHERE text LIKE ? OR tags LIKE ?"
            args = [f"%{like}%", f"%{like}%"]
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.db.execute(sql, args)]

    # --- задачи
    def todo_add(self, text: str, due: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO todos(ts, text, due) VALUES(?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), text, due),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def todo_list(self, include_done: bool = False) -> list[dict]:
        sql = "SELECT * FROM todos"
        if not include_done:
            sql += " WHERE done=0"
        sql += " ORDER BY done, due IS NULL, due, id"
        return [dict(r) for r in self.db.execute(sql)]

    def todo_done(self, todo_id: int) -> bool:
        cur = self.db.execute(
            "UPDATE todos SET done=1, done_ts=? WHERE id=? AND done=0",
            (datetime.now().isoformat(timespec="seconds"), todo_id),
        )
        self.db.commit()
        return cur.rowcount > 0


# ================================================================ агент
@dataclass
class Agent:
    id: str
    name: str
    category: str
    description: str
    run: Callable[["Context", str], Any]
    keywords: tuple = ()
    examples: tuple = ()
    needs: tuple = ()      # llm / net / fs-write / homelab / adb
    tags: tuple = ()
    secret: bool = False   # не писать запрос/ответ в журнал

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9]+\.[a-z0-9_]+", self.id):
            raise ValueError(f"плохой id агента: {self.id!r}")
        self._idx = {
            "id": set(norm_tokens(self.id.replace(".", " "))),
            "name": set(norm_tokens(self.name)),
            "kw": set(norm_tokens(" ".join(self.keywords))),
            "tags": set(norm_tokens(" ".join(self.tags))),
            "desc": set(norm_tokens(self.description)),
        }

    # --- релевантность запросу
    def score(self, query: str) -> float:
        qt = norm_tokens(query)
        if not qt:
            return 0.0
        qs = set(qt)
        idx = self._idx
        hit = (
            4.0 * len(qs & idx["id"])
            + 3.0 * len(qs & idx["name"])
            + 3.5 * len(qs & idx["kw"])
            + 1.5 * len(qs & idx["tags"])
            + 1.0 * len(qs & idx["desc"])
        )
        score = hit / (len(qs) ** 0.5)
        low = " " + query.lower() + " "
        if self.id in low or self.id in low.replace(" ", "."):
            score += 12.0
        for kw in self.keywords:
            kwl = kw.lower()
            if len(kwl) >= 4 and kwl in low:
                score += 1.2
        return round(score, 3)

    def row(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "description": self.description, "needs": list(self.needs),
            "keywords": list(self.keywords), "examples": list(self.examples),
        }


# ================================================================ реестр
class Registry:
    def __init__(self) -> None:
        self._items: dict[str, Agent] = {}

    def add(self, a: Agent) -> Agent:
        if a.id in self._items:
            raise ValueError(f"дубликат id агента: {a.id}")
        self._items[a.id] = a
        return a

    def get(self, agent_id: str) -> Agent | None:
        if agent_id in self._items:
            return self._items[agent_id]
        low = agent_id.lower()
        for a in self._items.values():
            if a.id.lower() == low or a.name.lower() == low:
                return a
        return None

    def all(self) -> list[Agent]:
        return sorted(self._items.values(), key=lambda a: (a.category, a.id))

    def categories(self) -> dict[str, list[Agent]]:
        out: dict[str, list[Agent]] = {}
        for a in self.all():
            out.setdefault(a.category, []).append(a)
        return out

    def __len__(self) -> int:
        return len(self._items)

    def route(self, query: str, k: int = 5) -> list[tuple[Agent, float]]:
        # пути и URL не должны влиять на выбор агента: «…/CHANGELOG.md» — это файл, не тема
        clean = re.sub(r"\S*[/\\]\S*", " ", query or "")
        clean = re.sub(r"\S+@\S+", " ", clean)
        scored = [(a, a.score(clean)) for a in self._items.values()]
        scored = [x for x in scored if x[1] > 0]
        scored.sort(key=lambda x: (-x[1], x[0].id))
        return scored[:k]


REGISTRY = Registry()


def agent(agent_id: str, name: str, category: str, description: str, *,
          keywords: Iterable[str] = (), examples: Iterable[str] = (),
          needs: Iterable[str] = (), tags: Iterable[str] = (),
          secret: bool = False):
    """Декоратор регистрации мини-агента."""
    def deco(fn: Callable[[ "Context", str], Any]):
        REGISTRY.add(Agent(
            id=agent_id, name=name, category=category, description=description,
            run=fn, keywords=tuple(keywords), examples=tuple(examples),
            needs=tuple(needs), tags=tuple(tags), secret=secret,
        ))
        return fn
    return deco


# ================================================================ контекст
@dataclass
class Context:
    cfg: dict
    data: Path = DATA
    out: Path = OUT
    dry_run: bool = True
    memory: Memory | None = None
    log: list[str] = field(default_factory=list)
    llm_client: Any = None

    def note(self, msg: str) -> None:
        self.log.append(msg)

    @property
    def network(self) -> str:
        return self.cfg.get("network", "192.168.1.0/24")


def make_context(cfg: dict | None = None, dry_run: bool | None = None,
                 memory: Memory | None = None) -> Context:
    cfg = cfg or load_config()
    if dry_run is None:
        dry_run = bool(cfg.get("safety", {}).get("dry_run_default", True))
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        try:
            save_config(cfg)
        except OSError:
            pass
    return Context(cfg=cfg, data=DATA, out=OUT, dry_run=dry_run,
                   memory=memory or Memory())


# ================================================================ исполнение
def run_agent(a: Agent, ctx: Context, text: str) -> Result:
    started = time.perf_counter()
    res = Result(agent=a.id)
    try:
        out = a.run(ctx, text)
        res.output = out
        res.ok = True
    except Exception as exc:  # агент не должен ронять ядро
        res.ok = False
        res.error = f"{type(exc).__name__}: {exc}"
        if os.environ.get("AGENTOS_DEBUG"):
            res.notes.append(traceback.format_exc())
    res.ms = int((time.perf_counter() - started) * 1000)
    if ctx.memory:
        try:
            logged_q = "[скрыто]" if a.secret else text
            logged_out = "[скрыто]" if a.secret else (res.output if res.ok else res.error)
            ctx.memory.log_run(a.id, res.ok, res.ms, logged_q, logged_out)
        except sqlite3.Error:
            pass
    return res


def answer(ctx: Context, query: str, *, agent_id: str | None = None,
           k: int = 3, min_score: float = 3.0) -> dict:
    """Маршрутизация запроса и выполнение. Возвращает структурированный ответ."""
    if not (query or "").strip() and not agent_id:
        return {"ok": False, "error": "пустой запрос", "agent": None,
                "suggestions": [{"id": a.id, "name": a.name, "score": s}
                                for a, s in REGISTRY.route("помощь", 5)]}
    if agent_id:
        target = REGISTRY.get(agent_id)
        if not target:
            return {"ok": False, "error": f"агент {agent_id!r} не найден",
                    "suggestions": _suggest(query or agent_id)}
        ranked = [(target, 1.0)]
    else:
        ranked = REGISTRY.route(query, k)
    if not ranked:
        return {"ok": False, "error": "нет подходящего агента",
                "suggestions": _suggest(query)}

    best, score = ranked[0]
    if not agent_id and score < min_score:
        return {
            "ok": False,
            "error": "запрос неоднозначен, уточните",
            "agent": None,
            "suggestions": [{"id": a.id, "name": a.name, "score": s}
                            for a, s in ranked],
        }
    res = run_agent(best, ctx, query)
    return {
        "ok": res.ok,
        "agent": best.id,
        "name": best.name,
        "score": score,
        "ms": res.ms,
        "output": res.output if res.ok else None,
        "error": res.error,
        "notes": res.notes,
        "alternatives": [{"id": a.id, "name": a.name, "score": s}
                         for a, s in ranked[1:]],
    }


def _suggest(query: str) -> list[dict]:
    ranked = REGISTRY.route(query, 5) or [(a, 0.0) for a in REGISTRY.all()[:5]]
    return [{"id": a.id, "name": a.name, "score": s} for a, s in ranked]


# ================================================================ загрузка
_loaded = False


def load_agents() -> Registry:
    global _loaded
    if _loaded:
        return REGISTRY
    import importlib
    import pkgutil
    from . import agents as pkg
    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name.startswith("_"):
            continue
        importlib.import_module(f"{pkg.__name__}.{mod.name}")
    _loaded = True
    return REGISTRY
