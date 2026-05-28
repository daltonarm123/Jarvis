"""SQLite memory store.

Three tables:
- conversations:  every user/assistant message with which agent handled it
- facts:          key/value store for things Jarvis should "just remember"
- agent_state:    per-agent scratch state (json blob)
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    session_id TEXT NOT NULL,
    agent TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_session_ts ON conversations(session_id, ts);

CREATE TABLE IF NOT EXISTS facts (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_state (
    agent TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated REAL NOT NULL
);
"""


class MemoryStore:
    def __init__(self, path: str | Path = "./data/jarvis.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # ---------- conversations ----------

    def add_message(
        self, session_id: str, role: str, content: str, agent: Optional[str] = None
    ) -> None:
        self._conn.execute(
            "INSERT INTO conversations (ts, session_id, agent, role, content) VALUES (?, ?, ?, ?, ?)",
            (time.time(), session_id, agent, role, content),
        )
        self._conn.commit()

    def recent_messages(
        self, session_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT ts, agent, role, content FROM conversations "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [
            {"ts": r[0], "agent": r[1], "role": r[2], "content": r[3]}
            for r in reversed(rows)
        ]

    # ---------- facts ----------

    def set_fact(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT INTO facts(key, value, updated) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
            (key, json.dumps(value), time.time()),
        )
        self._conn.commit()

    def get_fact(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM facts WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row[0]) if row else default

    def all_facts(self) -> Dict[str, Any]:
        return {
            k: json.loads(v)
            for k, v in self._conn.execute("SELECT key, value FROM facts")
        }

    # ---------- agent state ----------

    def set_agent_state(self, agent: str, state: Dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO agent_state(agent, state_json, updated) VALUES(?, ?, ?) "
            "ON CONFLICT(agent) DO UPDATE SET state_json=excluded.state_json, updated=excluded.updated",
            (agent, json.dumps(state), time.time()),
        )
        self._conn.commit()

    def get_agent_state(self, agent: str) -> Dict[str, Any]:
        row = self._conn.execute(
            "SELECT state_json FROM agent_state WHERE agent = ?", (agent,)
        ).fetchone()
        return json.loads(row[0]) if row else {}

    def close(self) -> None:
        self._conn.close()
