"""备份与导入导出。

- 每日首次启动自动备份数据库到 backups/。
- 手动导出/导入：单空间 JSON 或整体 ZIP。
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from . import paths
from .database import Database, now_iso
from .logger import get_logger


def daily_backup(db: Database) -> Path | None:
    """每日首次启动备份，返回备份文件路径；今天已备份则返回 None。"""
    today = datetime.now().strftime("%Y%m%d")
    backups = paths.backups_dir()
    backups.mkdir(parents=True, exist_ok=True)
    marker = backups / f".last_backup_{today}"
    if marker.exists():
        return None

    dest = backups / f"aiworkbench_{today}.db"
    _backup_sqlite(db.db_path, dest)
    marker.write_text(now_iso(), encoding="utf-8")
    get_logger().info("完成每日备份: %s", dest)
    return dest


def _backup_sqlite(src: Path, dest: Path) -> None:
    """使用 SQLite 在线备份 API，保证一致性。"""
    src_conn = sqlite3.connect(str(src))
    dest_conn = sqlite3.connect(str(dest))
    try:
        src_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        src_conn.close()


# ------------------------------------------------------------------ 导出/导入
def export_space(db: Database, space_id: str, out_path: str | Path) -> Path:
    """导出单个空间为 JSON。"""
    space = db.get_space(space_id)
    if space is None:
        raise ValueError("空间不存在")
    data: dict[str, Any] = {
        "format": "aiworkbench-space",
        "version": 1,
        "exported_at": now_iso(),
        "space": space,
        "conversations": db.list_conversations(space_id),
        "messages": [],
        "memory_nodes": db.list_memory_nodes(space_id),
        "memory_edges": db.list_memory_edges(space_id),
    }
    for conv in data["conversations"]:
        data["messages"].extend(db.list_messages(conv["id"]))

    out_path = Path(out_path)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def import_space(db: Database, json_path: str | Path) -> str:
    """从 JSON 导入单个空间，返回新空间 id。导入时重新生成所有 id。"""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    space_name = data.get("space", {}).get("name", "导入的空间")
    new_space = db.create_space(space_name)
    new_space_id = new_space["id"]

    conv_id_map: dict[str, str] = {}
    for conv in data.get("conversations", []):
        new_conv = db.create_conversation(new_space_id, conv.get("title", "新对话"))
        conv_id_map[conv["id"]] = new_conv["id"]

    msg_id_map: dict[str, str] = {}
    for msg in data.get("messages", []):
        new_msg = db.add_message(
            conv_id_map.get(msg["conversation_id"], ""),
            msg.get("role", "user"),
            msg.get("content", ""),
            msg.get("memory_json"),
        )
        msg_id_map[msg["id"]] = new_msg["id"]

    node_id_map: dict[str, str] = {}
    for node in data.get("memory_nodes", []):
        new_node = db.add_memory_node(
            space_id=new_space_id,
            label=node.get("label", ""),
            node_type=node.get("type", "note"),
            metadata=node.get("metadata", {}),
            source_message_id=msg_id_map.get(node.get("source_message_id")),
            x=node.get("x"),
            y=node.get("y"),
        )
        node_id_map[node["id"]] = new_node["id"]

    for edge in data.get("memory_edges", []):
        src = node_id_map.get(edge["source_node_id"])
        dst = node_id_map.get(edge["target_node_id"])
        if src and dst:
            db.add_memory_edge(new_space_id, src, dst, edge.get("relation_type", "related"))

    return new_space_id


def export_all(db: Database, out_path: str | Path) -> Path:
    """整体打包为 ZIP（含数据库 + 全部空间 JSON）。"""
    out_path = Path(out_path)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 打包数据库
        zf.write(db.db_path, arcname="aiworkbench.db")
        # 打包每个空间
        for space in db.list_spaces():
            tmp_space = out_path.with_suffix(".space.json")
            export_space(db, space["id"], tmp_space)
            zf.write(tmp_space, arcname=f"spaces/{space['id']}.json")
            tmp_space.unlink(missing_ok=True)
    return out_path


def import_all(db: Database, zip_path: str | Path) -> int:
    """从 ZIP 导入，返回导入的空间数量。"""
    zip_path = Path(zip_path)
    count = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".json") and name.startswith("spaces/"):
                data = zf.read(name).decode("utf-8")
                tmp = zip_path.with_name("_import_space.json")
                tmp.write_text(data, encoding="utf-8")
                import_space(db, tmp)
                tmp.unlink(missing_ok=True)
                count += 1
    return count