from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class Storage:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at REAL NOT NULL,
                tags TEXT DEFAULT ''
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS timers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT,
                due_at REAL NOT NULL,
                created_at REAL NOT NULL,
                fired INTEGER DEFAULT 0
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS reminders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                due_at REAL,
                created_at REAL NOT NULL,
                done INTEGER DEFAULT 0
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS kv(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                meta TEXT DEFAULT '{}',
                created_at REAL NOT NULL
            )""")

    # notes
    def add_note(self, text: str, tags: str = "") -> int:
        with self._conn() as c:
            cur = c.execute("INSERT INTO notes(text,created_at,tags) VALUES(?,?,?)",
                            (text, time.time(), tags))
            return int(cur.lastrowid)

    def list_notes(self, limit: int = 20, query: str = "") -> List[Dict[str, Any]]:
        with self._conn() as c:
            if query:
                q = f"%{query}%"
                rows = c.execute("SELECT * FROM notes WHERE text LIKE ? ORDER BY id DESC LIMIT ?",
                                 (q, limit)).fetchall()
            else:
                rows = c.execute("SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def delete_note(self, note_id: int) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM notes WHERE id=?", (note_id,))
            return cur.rowcount > 0

    # timers
    def add_timer(self, label: str, due_at: float) -> int:
        with self._conn() as c:
            cur = c.execute("INSERT INTO timers(label,due_at,created_at,fired) VALUES(?,?,?,0)",
                            (label, due_at, time.time()))
            return int(cur.lastrowid)

    def list_timers(self, active_only: bool = True) -> List[Dict[str, Any]]:
        with self._conn() as c:
            if active_only:
                rows = c.execute("SELECT * FROM timers WHERE fired=0 ORDER BY due_at ASC").fetchall()
            else:
                rows = c.execute("SELECT * FROM timers ORDER BY id DESC LIMIT 50").fetchall()
        return [dict(r) for r in rows]

    def fire_due_timers(self, now: Optional[float] = None) -> List[Dict[str, Any]]:
        now = now or time.time()
        with self._conn() as c:
            rows = c.execute("SELECT * FROM timers WHERE fired=0 AND due_at<=?", (now,)).fetchall()
            ids = [r["id"] for r in rows]
            if ids:
                c.executemany("UPDATE timers SET fired=1 WHERE id=?", [(i,) for i in ids])
        return [dict(r) for r in rows]

    def cancel_timer(self, timer_id: int) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM timers WHERE id=?", (timer_id,))
            return cur.rowcount > 0

    # kv
    def set(self, key: str, value: Any):
        with self._conn() as c:
            c.execute("INSERT INTO kv(key,value,updated_at) VALUES(?,?,?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                      (key, json.dumps(value, ensure_ascii=False), time.time()))

    def get(self, key: str, default: Any = None) -> Any:
        with self._conn() as c:
            row = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except Exception:
            return default

    # history
    def add_history(self, role: str, text: str, meta: Optional[Dict[str, Any]] = None):
        with self._conn() as c:
            c.execute("INSERT INTO history(role,text,meta,created_at) VALUES(?,?,?,?)",
                      (role, text, json.dumps(meta or {}, ensure_ascii=False), time.time()))

    def recent_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in reversed(rows)]
