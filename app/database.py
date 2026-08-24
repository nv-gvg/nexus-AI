"""SQLite 数据访问层。

数据模型:
    spaces          id, name, created_at
    conversations   id, space_id, title, created_at
    messages        id, conversation_id, role, content, memory_json, created_at
    memory_nodes    id, space_id, label, type, metadata, source_message_id, x, y, created_at
    memory_edges    id, space_id, source_node_id, target_node_id, relation_type
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .logger import get_logger


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex


_SCHEMA = """
CREATE TABLE IF NOT EXISTS spaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    space_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(space_id) REFERENCES spaces(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    memory_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS memory_nodes (
    id TEXT PRIMARY KEY,
    space_id TEXT NOT NULL,
    label TEXT NOT NULL,
    type TEXT,
    metadata TEXT,
    source_message_id TEXT,
    x REAL,
    y REAL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory_edges (
    id TEXT PRIMARY KEY,
    space_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    relation_type TEXT
);
CREATE TABLE IF NOT EXISTS space_meta (
    space_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY(space_id, key)
);
CREATE INDEX IF NOT EXISTS idx_conversations_space ON conversations(space_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_memory_nodes_space ON memory_nodes(space_id);
CREATE INDEX IF NOT EXISTS idx_memory_edges_space ON memory_edges(space_id);
"""


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.log = get_logger()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _exec(self, sql: str, params: tuple = ()) -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def _query_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        rows = self._query(sql, params)
        return rows[0] if rows else None

    # ------------------------------------------------------------------ 空间
    def create_space(self, name: str) -> dict[str, Any]:
        sid = new_id()
        self._exec(
            "INSERT INTO spaces (id, name, created_at) VALUES (?, ?, ?)",
            (sid, name, now_iso()),
        )
        return {"id": sid, "name": name, "created_at": now_iso()}

    def rename_space(self, space_id: str, name: str) -> None:
        self._exec("UPDATE spaces SET name = ? WHERE id = ?", (name, space_id))

    def delete_space(self, space_id: str) -> None:
        self._exec("DELETE FROM spaces WHERE id = ?", (space_id,))

    def list_spaces(self) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM spaces ORDER BY created_at ASC")

    def get_space(self, space_id: str) -> dict[str, Any] | None:
        return self._query_one("SELECT * FROM spaces WHERE id = ?", (space_id,))

    # ------------------------------------------------------------------ 对话
    def create_conversation(self, space_id: str, title: str = "新对话") -> dict[str, Any]:
        cid = new_id()
        self._exec(
            "INSERT INTO conversations (id, space_id, title, created_at) VALUES (?, ?, ?, ?)",
            (cid, space_id, title, now_iso()),
        )
        return {"id": cid, "space_id": space_id, "title": title, "created_at": now_iso()}

    def rename_conversation(self, conversation_id: str, title: str) -> None:
        self._exec("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))

    def delete_conversation(self, conversation_id: str) -> None:
        self._exec("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    def list_conversations(self, space_id: str) -> list[dict[str, Any]]:
        return self._query(
            "SELECT * FROM conversations WHERE space_id = ? ORDER BY created_at DESC",
            (space_id,),
        )

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        return self._query_one("SELECT * FROM conversations WHERE id = ?", (conversation_id,))

    # ------------------------------------------------------------------ 消息
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        memory_json: str | None = None,
    ) -> dict[str, Any]:
        mid = new_id()
        created = now_iso()
        self._exec(
            "INSERT INTO messages (id, conversation_id, role, content, memory_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (mid, conversation_id, role, content, memory_json, created),
        )
        return {
            "id": mid,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "memory_json": memory_json,
            "created_at": created,
        }

    def update_message_content(self, message_id: str, content: str) -> None:
        self._exec("UPDATE messages SET content = ? WHERE id = ?", (content, message_id))

    def update_message_memory(self, message_id: str, memory_json: str) -> None:
        self._exec("UPDATE messages SET memory_json = ? WHERE id = ?", (memory_json, message_id))

    def delete_message(self, message_id: str) -> None:
        self._exec("DELETE FROM messages WHERE id = ?", (message_id,))

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        return self._query(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )

    # ------------------------------------------------------------------ 空间元数据（自动记忆游标等）
    def get_space_meta(self, space_id: str, key: str) -> str | None:
        row = self._query_one(
            "SELECT value FROM space_meta WHERE space_id = ? AND key = ?",
            (space_id, key),
        )
        return row["value"] if row else None

    def set_space_meta(self, space_id: str, key: str, value: str) -> None:
        self._exec(
            "INSERT INTO space_meta (space_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(space_id, key) DO UPDATE SET value = excluded.value",
            (space_id, key, value),
        )

    def count_user_messages(self, space_id: str) -> int:
        row = self._query_one(
            "SELECT COUNT(*) AS n FROM messages m "
            "JOIN conversations c ON m.conversation_id = c.id "
            "WHERE c.space_id = ? AND m.role = 'user'",
            (space_id,),
        )
        return int(row["n"]) if row else 0

    def last_auto_memory_count(self, space_id: str) -> int:
        val = self.get_space_meta(space_id, "auto_memory_count")
        return int(val) if val and val.isdigit() else 0

    def record_auto_memory_count(self, space_id: str) -> None:
        self.set_space_meta(space_id, "auto_memory_count", str(self.count_user_messages(space_id)))

    def recent_turn_payload(self, space_id: str, limit: int = 6) -> list[dict[str, Any]]:
        """取空间最近一组消息（按时间倒序取 limit 条，再正序返回），用于自动总结。"""
        rows = self._query(
            "SELECT m.role, m.content FROM messages m "
            "JOIN conversations c ON m.conversation_id = c.id "
            "WHERE c.space_id = ? ORDER BY m.created_at DESC LIMIT ?",
            (space_id, limit),
        )
        rows.reverse()
        return rows

    # ------------------------------------------------------------------ 记忆节点
    def add_memory_node(
        self,
        space_id: str,
        label: str,
        node_type: str = "note",
        metadata: dict[str, Any] | None = None,
        source_message_id: str | None = None,
        x: float | None = None,
        y: float | None = None,
    ) -> dict[str, Any]:
        nid = new_id()
        created = now_iso()
        self._exec(
            "INSERT INTO memory_nodes"
            " (id, space_id, label, type, metadata, source_message_id, x, y, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                nid,
                space_id,
                label,
                node_type,
                json.dumps(metadata or {}, ensure_ascii=False),
                source_message_id,
                x,
                y,
                created,
            ),
        )
        return {
            "id": nid,
            "space_id": space_id,
            "label": label,
            "type": node_type,
            "metadata": metadata or {},
            "source_message_id": source_message_id,
            "x": x,
            "y": y,
            "created_at": created,
        }

    def update_memory_node(
        self, node_id: str, label: str | None = None, x: float | None = None, y: float | None = None
    ) -> None:
        if label is not None:
            self._exec("UPDATE memory_nodes SET label = ? WHERE id = ?", (label, node_id))
        if x is not None and y is not None:
            self._exec("UPDATE memory_nodes SET x = ?, y = ? WHERE id = ?", (x, y, node_id))

    def delete_memory_node(self, node_id: str) -> None:
        self._exec("DELETE FROM memory_edges WHERE source_node_id = ? OR target_node_id = ?",
                   (node_id, node_id))
        self._exec("DELETE FROM memory_nodes WHERE id = ?", (node_id,))

    def get_memory_node(self, node_id: str) -> dict[str, Any] | None:
        node = self._query_one("SELECT * FROM memory_nodes WHERE id = ?", (node_id,))
        if node and node.get("metadata"):
            node["metadata"] = json.loads(node["metadata"])
        return node

    def list_memory_nodes(self, space_id: str) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM memory_nodes WHERE space_id = ? ORDER BY created_at ASC", (space_id,)
        )
        for r in rows:
            r["metadata"] = json.loads(r["metadata"]) if r.get("metadata") else {}
        return rows

    def add_memory_edge(
        self, space_id: str, source_node_id: str, target_node_id: str, relation_type: str = "related"
    ) -> dict[str, Any]:
        eid = new_id()
        self._exec(
            "INSERT INTO memory_edges (id, space_id, source_node_id, target_node_id, relation_type)"
            " VALUES (?, ?, ?, ?, ?)",
            (eid, space_id, source_node_id, target_node_id, relation_type),
        )
        return {
            "id": eid,
            "space_id": space_id,
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "relation_type": relation_type,
        }

    def delete_memory_edge(self, edge_id: str) -> None:
        self._exec("DELETE FROM memory_edges WHERE id = ?", (edge_id,))

    def list_memory_edges(self, space_id: str) -> list[dict[str, Any]]:
        return self._query(
            "SELECT * FROM memory_edges WHERE space_id = ?", (space_id,)
        )

    def get_graph(self, space_id: str) -> dict[str, Any]:
        return {
            "nodes": self.list_memory_nodes(space_id),
            "edges": self.list_memory_edges(space_id),
        }

    # ------------------------------------------------------------------ 搜索
    def search_messages(self, space_id: str, keyword: str) -> list[dict[str, Any]]:
        like = f"%{keyword}%"
        return self._query(
            "SELECT m.*, c.title AS conversation_title FROM messages m"
            " JOIN conversations c ON m.conversation_id = c.id"
            " WHERE c.space_id = ? AND m.content LIKE ? ORDER BY m.created_at DESC",
            (space_id, like),
        )

    def global_search(self, keyword: str) -> list[dict[str, Any]]:
        like = f"%{keyword}%"
        return self._query(
            "SELECT m.*, c.title AS conversation_title, s.name AS space_name FROM messages m"
            " JOIN conversations c ON m.conversation_id = c.id"
            " JOIN spaces s ON c.space_id = s.id"
            " WHERE m.content LIKE ? ORDER BY m.created_at DESC",
            (like,),
        )

    def count_memory_nodes(self, space_id: str) -> int:
        row = self._query_one(
            "SELECT COUNT(*) AS n FROM memory_nodes WHERE space_id = ?", (space_id,)
        )
        return int(row["n"]) if row else 0