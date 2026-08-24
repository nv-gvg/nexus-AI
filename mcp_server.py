"""Nexus-AI 的 MCP 服务器。

把本地的空间与知识图谱记忆以 MCP 工具形式暴露给其它 AI 客户端
（Claude Desktop、Cursor、Nexus-AI 自身等）。

使用方法（stdio 传输，直接运行）：
    python mcp_server.py

在其它客户端中把它配置为 stdio 服务器即可。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让本脚本能作为独立子进程 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastmcp import FastMCP  # noqa: E402

from app import paths  # noqa: E402
from app.database import Database  # noqa: E402

mcp = FastMCP("Nexus-AI-Memory")


def _db() -> Database:
    return Database(paths.db_path())


@mcp.tool()
def list_spaces() -> str:
    """列出所有空间及其 id 和名称。调用前可用此了解有哪些空间。"""
    db = _db()
    spaces = db.list_spaces()
    if not spaces:
        return "(暂无空间)"
    return "\n".join(f"{s['id']} | {s['name']}" for s in spaces)


@mcp.tool()
def list_memory(space_id: str) -> str:
    """列出指定空间的所有记忆节点。space_id 可通过 list_spaces 获取。"""
    db = _db()
    nodes = db.list_memory_nodes(space_id)
    if not nodes:
        return "(该空间暂无记忆)"
    lines = []
    for n in nodes:
        lines.append(f"[{n['id']}] ({n.get('type', '')}) {n.get('label', '')}")
    return "\n".join(lines)


@mcp.tool()
def search_memory(space_id: str, query: str) -> str:
    """在指定空间按关键词搜索记忆节点，返回匹配节点的内容。"""
    db = _db()
    nodes = db.list_memory_nodes(space_id)
    q = query.lower()
    matched = [
        n
        for n in nodes
        if q in (n.get("label", "") or "").lower()
        or q in str(n.get("metadata", {})).lower()
    ]
    if not matched:
        return "(未找到匹配的记忆)"
    lines = []
    for n in matched:
        meta = n.get("metadata", {})
        content = meta.get("memory", "") if isinstance(meta, dict) else str(meta)
        lines.append(f"{n.get('label', '')}：{content}" if content else n.get("label", ""))
    return "\n\n".join(lines)


@mcp.tool()
def add_memory(space_id: str, label: str, content: str = "") -> str:
    """在指定空间新增一条记忆节点。label 为简短标题，content 为记忆详情。"""
    db = _db()
    node = db.add_memory_node(
        space_id=space_id,
        label=label,
        node_type="external",
        metadata={"memory": content or label},
    )
    return f"已新增记忆节点：{node['id']} | {label}"


if __name__ == "__main__":
    mcp.run()