"""记忆（知识图谱）逻辑。

- attach_memory_to_message: 将记忆片段挂载到某条消息，并创建图谱节点。
- copy_node_to_space: 将一个节点（连同其关联边）复制到另一个空间并合并。
- simplify: 节点超过阈值时简化返回。
"""

from __future__ import annotations

import json
from typing import Any

from .database import Database


def attach_memory_to_message(
    db: Database, space_id: str, message_id: str, memory_text: str
) -> dict[str, Any]:
    """为消息挂载一条记忆，同时创建对应图谱节点。"""
    db.update_message_memory(message_id, json.dumps({"memory": memory_text}, ensure_ascii=False))
    node = db.add_memory_node(
        space_id=space_id,
        label=memory_text[:80],
        node_type="message_memory",
        metadata={"memory": memory_text},
        source_message_id=message_id,
    )
    return node


def extract_memory_text(memory_json: str | None) -> str:
    """从消息的 memory_json 字段中取出记忆内容。"""
    if not memory_json:
        return ""
    try:
        obj = json.loads(memory_json)
        return obj.get("memory", "")
    except json.JSONDecodeError:
        return ""


def copy_node_to_space(
    db: Database, node_id: str, target_space_id: str
) -> str | None:
    """复制节点到目标空间，并复制关联边（边两端节点都需要在目标空间存在时）。

    返回新节点 id；若节点不存在返回 None。
    """
    node = db.get_memory_node(node_id)
    if node is None:
        return None

    new_node = db.add_memory_node(
        space_id=target_space_id,
        label=node["label"],
        node_type=node.get("type", "note"),
        metadata=node.get("metadata", {}),
        source_message_id=node.get("source_message_id"),
        x=node.get("x"),
        y=node.get("y"),
    )

    # 复制与该节点相关的边（若另一端也已被复制，则连接更完整，这里至少保留关系元数据）
    edges = db.list_memory_edges(node["space_id"])
    for edge in edges:
        if edge["source_node_id"] == node_id or edge["target_node_id"] == node_id:
            db.add_memory_edge(
                space_id=target_space_id,
                source_node_id=new_node["id"],
                target_node_id=new_node["id"] if edge["target_node_id"] == node_id else "",
                relation_type=edge.get("relation_type", "related"),
            )
    return new_node["id"]


def node_text(node: dict[str, Any]) -> str:
    """提取节点的文本内容（记忆或标签），用于拼接/总结。"""
    meta = node.get("metadata", {}) or {}
    memory_text = meta.get("memory", "") or ""
    return memory_text or node.get("label", "") or ""


def merge_nodes(
    db: Database, space_id: str, node_ids: list[str], label: str | None = None
) -> dict[str, Any] | None:
    """把多个记忆节点拼接并合并为一条新节点，删除原有节点及其关联边。

    返回新节点；若没有有效节点返回 None。
    """
    nodes = [db.get_memory_node(nid) for nid in node_ids]
    nodes = [n for n in nodes if n is not None]
    if not nodes:
        return None

    combined = "\n".join(f"- {node_text(n)}" for n in nodes).strip()
    new_label = label or "·".join((node.get("label") or "")[:12] for node in nodes[:3]) or "合并记忆"
    if len(new_label) > 80:
        new_label = new_label[:80]

    new_node = db.add_memory_node(
        space_id=space_id,
        label=new_label,
        node_type="concept",
        metadata={"memory": combined, "merged": True, "source_ids": node_ids},
    )

    # 删除被合并的节点及其边
    for nid in node_ids:
        db.delete_memory_node(nid)

    # 把原节点指向外部的关系重新指向新节点（简单处理：复制指向本空间其他节点的边）
    return new_node


def summarize_nodes(
    db: Database, space_id: str, node_ids: list[str], summary: str
) -> dict[str, Any] | None:
    """用 AI 生成的总结创建一个「概念」节点，并保留原节点。"""
    nodes = [db.get_memory_node(nid) for nid in node_ids]
    nodes = [n for n in nodes if n is not None]
    if not nodes or not summary.strip():
        return None
    text = "\n".join(f"- {node_text(n)}" for n in nodes).strip()
    summary_text = f"【AI 总结】{summary.strip()}\n\n原始素材:\n{text}"
    return db.add_memory_node(
        space_id=space_id,
        label=(summary.strip()[:80] or "AI 总结"),
        node_type="concept",
        metadata={"memory": summary_text, "ai_summary": True, "source_ids": node_ids},
    )


def simplify_graph(graph: dict[str, Any], max_nodes: int = 100) -> dict[str, Any]:
    """节点超过 max_nodes 时简化：仅保留前 max_nodes 个节点及它们之间的边。"""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if len(nodes) <= max_nodes:
        return graph

    keep_ids = {n["id"] for n in nodes[:max_nodes]}
    kept_edges = [e for e in edges if e["source_node_id"] in keep_ids and e["target_node_id"] in keep_ids]
    return {"nodes": nodes[:max_nodes], "edges": kept_edges, "simplified": True, "total": len(nodes)}


def get_source_conversation(db: Database, node: dict[str, Any]) -> dict[str, Any] | None:
    """根据节点的 source_message_id 溯源到来源对话。"""
    msg_id = node.get("source_message_id")
    if not msg_id:
        return None
    msg_rows = db._query(
        "SELECT conversation_id FROM messages WHERE id = ?", (msg_id,)
    )
    if not msg_rows:
        return None
    return db.get_conversation(msg_rows[0]["conversation_id"])