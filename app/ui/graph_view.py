"""图形化记忆：知识图谱可视化。

- 节点可拖拽、点击查看详情、右键复制到其他空间。
- 超过 100 个节点自动简化显示。
"""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QInputDialog,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import memory
from .widgets import show_toast

NODE_RADIUS = 34


class NodeItem(QGraphicsEllipseItem):
    def __init__(self, node: dict[str, Any], view: "GraphView") -> None:
        super().__init__(-NODE_RADIUS, -NODE_RADIUS, 2 * NODE_RADIUS, 2 * NODE_RADIUS)
        self.node_id = node["id"]
        self.node = node
        self.view = view

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        color = self._color_for_type(node.get("type", "note"))
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor("#20242e"), 1.5))

        short = (node.get("label") or "节点")[:10]
        text = QGraphicsSimpleTextItem(short, self)
        text.setBrush(QBrush(QColor("#fff")))
        rect = text.boundingRect()
        text.setPos(-rect.width() / 2, -rect.height() / 2)

    @staticmethod
    def _color_for_type(node_type: str) -> str:
        palette = {
            "message_memory": "#1565c0",
            "note": "#2e7d32",
            "concept": "#ef6c00",
            "entity": "#6a1b9a",
            "default": "#546e7a",
        }
        return palette.get(node_type, palette["default"])

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.view.update_edges()
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        self.view.persist_node(self.node_id, self.pos())

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self.view.open_node_menu(self.node_id, event.screenPos())


class GraphView(QWidget):
    node_clicked = pyqtSignal(dict)

    def __init__(self, db, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.space_id: str | None = None
        self.node_items: dict[str, NodeItem] = {}
        self.edge_items: list[tuple[Any, QGraphicsLineItem]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.info_label = QLabel("选择空间查看记忆图谱")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: #8b92a0;")
        layout.addWidget(self.info_label)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        layout.addWidget(self.view)

    # ------------------------------------------------------------------ 加载
    def set_space(self, space_id: str | None) -> None:
        self.space_id = space_id
        self.refresh()

    def refresh(self) -> None:
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        if not self.space_id:
            self.info_label.setText("选择空间查看记忆图谱")
            self.view.hide()
            self.info_label.show()
            return

        graph = self.db.get_graph(self.space_id)
        graph = memory.simplify_graph(graph, max_nodes=100)

        if not graph["nodes"]:
            self.view.hide()
            self.info_label.setText("当前空间还没有记忆")
            self.info_label.show()
            return

        self.view.show()
        self.info_label.hide()

        # 布局节点
        positions: dict[str, QPointF] = {}
        n = len(graph["nodes"])
        for i, node in enumerate(graph["nodes"]):
            if node.get("x") is not None and node.get("y") is not None:
                pos = QPointF(node["x"], node["y"])
            else:
                angle = 2 * math.pi * i / max(n, 1)
                radius = 60 + 40 * math.sqrt(n)
                pos = QPointF(radius * math.cos(angle), radius * math.sin(angle))
            positions[node["id"]] = pos
            item = NodeItem(node, self)
            item.setPos(pos)
            self.scene.addItem(item)
            self.node_items[node["id"]] = item

        # 连线
        for edge in graph["edges"]:
            src = self.node_items.get(edge["source_node_id"])
            dst = self.node_items.get(edge["target_node_id"])
            if src and dst and src is not dst:
                line = QGraphicsLineItem()
                line.setPen(QPen(QColor("#3a4152"), 1.5))
                self.scene.addItem(line)
                self.edge_items.append((edge, line))

        self.update_edges()
        if graph.get("simplified"):
            show_toast(self, f"记忆节点较多，已简化显示前 100 个（共 {graph['total']} 个）")

    def update_edges(self) -> None:
        for edge, line in self.edge_items:
            src = self.node_items.get(edge["source_node_id"])
            dst = self.node_items.get(edge["target_node_id"])
            if src and dst:
                line.setLine(src.pos().x(), src.pos().y(), dst.pos().x(), dst.pos().y())

    def persist_node(self, node_id: str, pos: QPointF) -> None:
        self.db.update_memory_node(node_id, x=pos.x(), y=pos.y())

    # ------------------------------------------------------------------ 交互
    def open_node_menu(self, node_id: str, global_pos) -> None:
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        view_action = menu.addAction("查看详情")
        copy_action = menu.addAction("复制节点到其他空间")
        delete_action = menu.addAction("删除节点")
        chosen = menu.exec(global_pos)

        if chosen == view_action:
            node = self.db.get_memory_node(node_id)
            if node:
                self.node_clicked.emit(node)
        elif chosen == copy_action:
            self.copy_node_to_space(node_id)
        elif chosen == delete_action:
            self.db.delete_memory_node(node_id)
            self.refresh()
            show_toast(self, "已删除节点")

    def copy_node_to_space(self, node_id: str) -> None:
        spaces = [s for s in self.db.list_spaces() if s["id"] != self.space_id]
        if not spaces:
            show_toast(self, "没有其他空间可复制", success=False)
            return
        names = [s["name"] for s in spaces]
        idx = 0
        name, ok = QInputDialog.getItem(self, "复制节点", "选择目标空间:", names, idx, False)
        if ok and name:
            target = next(s for s in spaces if s["name"] == name)
            new_id = memory.copy_node_to_space(self.db, node_id, target["id"])
            if new_id:
                show_toast(self, f"已复制到「{name}」")
            else:
                show_toast(self, "复制失败", success=False)