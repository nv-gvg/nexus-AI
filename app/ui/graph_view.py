"""图形化记忆：AIAgent 风格的自由画布知识图谱。

- 节点可拖拽，像拼图一样自由摆放/组装布局。
- 每个节点带一个「连接端口」：从端口拖到另一个节点即可建立关系连线。
- 滚轮缩放画布，中键拖拽平移视野。
- 点击节点查看详情、右键复制/删除，支持合并与 AI 总结所选。
"""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import QPointF, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import memory
from . import theme
from .widgets import show_toast

NODE_RADIUS = 34
PORT_RADIUS = 7


class SummarizeThread(QThread):
    """后台调用 AI 总结一组记忆节点。"""

    done = pyqtSignal(str)

    def __init__(self, node_texts: list[str]) -> None:
        super().__init__()
        self.node_texts = node_texts

    def run(self) -> None:
        from ..api_client import APIClient

        material = "\n".join(f"- {t}" for t in self.node_texts)
        prompt = (
            "请把下面这些零散的记忆整理成一段连贯、简洁的总结要点，"
            "保留关键信息，删除重复与冗余：\n" + material
        )
        try:
            result = APIClient().chat_text([{"role": "user", "content": prompt}])
        except Exception as exc:  # noqa: BLE001
            result = f"总结失败：{exc}"
        self.done.emit(result)


class AnchorItem(QGraphicsEllipseItem):
    """节点上的连接端口：从端口拖出到另一节点可建立连线。"""

    def __init__(self, node_item: "NodeItem") -> None:
        super().__init__(-PORT_RADIUS, -PORT_RADIUS, 2 * PORT_RADIUS, 2 * PORT_RADIUS, node_item)
        self.node_item = node_item
        self.view = node_item.view
        self._dragging = False
        self.setBrush(QBrush(QColor(theme.current().accent)))
        self.setPen(QPen(QColor(theme.current().surface_3), 1))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        # 端口放在节点右上角
        self.setPos(NODE_RADIUS - 4, -NODE_RADIUS + 4)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._dragging = True
        self.view.start_temp_edge(self.node_item, event.scenePos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
            self.view.update_temp_edge(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
            self._dragging = False
            self.view.finish_temp_edge(self.node_item, event.scenePos())
            # 端口复位，不随拖动走
            self.setPos(NODE_RADIUS - 4, -NODE_RADIUS + 4)
        super().mouseReleaseEvent(event)


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
        self.setPen(QPen(QColor(theme.current().border_light), 1.5))

        short = (node.get("label") or "节点")[:10]
        text = QGraphicsSimpleTextItem(short, self)
        text.setBrush(QBrush(QColor("#fff")))
        rect = text.boundingRect()
        text.setPos(-rect.width() / 2, -rect.height() / 2)

        # 连接端口
        self.anchor = AnchorItem(self)

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


class CanvasView(QGraphicsView):
    """支持缩放与平移的画布视图。"""

    def __init__(self, scene: QGraphicsScene, owner: "GraphView") -> None:
        super().__init__(scene)
        self._owner = owner
        self._panning = False
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event) -> None:  # noqa: N802
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_scale = self.transform().m11() * factor
        if 0.25 <= new_scale <= 4.0:
            self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._panning and event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            return
        super().mouseReleaseEvent(event)


class GraphView(QWidget):
    node_clicked = pyqtSignal(dict)

    def __init__(self, db, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panelRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.db = db
        self.space_id: str | None = None
        self.node_items: dict[str, NodeItem] = {}
        self.edge_items: list[tuple[Any, QGraphicsLineItem]] = []
        self._temp_edge: QGraphicsLineItem | None = None
        self._temp_src: NodeItem | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.info_label = QLabel("选择空间查看记忆图谱")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(f"color: {theme.current().text_dim};")
        layout.addWidget(self.info_label)

        # 操作工具栏
        toolbar = QHBoxLayout()
        merge_btn = QPushButton("合并所选")
        merge_btn.clicked.connect(self.merge_selected)
        summarize_btn = QPushButton("AI 总结所选")
        summarize_btn.clicked.connect(self.summarize_selected)
        self.zoom_in_btn = QPushButton("＋")
        self.zoom_in_btn.setFixedWidth(36)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn = QPushButton("－")
        self.zoom_out_btn.setFixedWidth(36)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.fit_btn = QPushButton("适配画布")
        self.fit_btn.clicked.connect(self.fit_view)
        toolbar.addWidget(merge_btn)
        toolbar.addWidget(summarize_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.fit_btn)
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.zoom_in_btn)
        layout.addLayout(toolbar)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(theme.current().bg))
        self.view = CanvasView(self.scene, self)
        self.view.setStyleSheet(
            f"QGraphicsView {{ background: {theme.current().bg}; border: none; }}"
        )
        layout.addWidget(self.view)

    # ------------------------------------------------------------------ 加载
    def set_space(self, space_id: str | None) -> None:
        self.space_id = space_id
        self.refresh()

    def refresh_theme(self) -> None:
        """主题切换后刷新图谱配色。"""
        self.info_label.setStyleSheet(f"color: {theme.current().text_dim};")
        self.view.setStyleSheet(
            f"QGraphicsView {{ background: {theme.current().bg}; border: none; }}"
        )
        self.scene.setBackgroundBrush(QColor(theme.current().bg))
        self.refresh()

    def refresh(self) -> None:
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        self._temp_edge = None
        self._temp_src = None
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
        n = len(graph["nodes"])
        for i, node in enumerate(graph["nodes"]):
            if node.get("x") is not None and node.get("y") is not None:
                pos = QPointF(node["x"], node["y"])
            else:
                angle = 2 * math.pi * i / max(n, 1)
                radius = 60 + 40 * math.sqrt(n)
                pos = QPointF(radius * math.cos(angle), radius * math.sin(angle))
            item = NodeItem(node, self)
            item.setPos(pos)
            self.scene.addItem(item)
            self.node_items[node["id"]] = item

        # 连线
        for edge in graph["edges"]:
            self._create_edge_item(edge)

        self.update_edges()
        if graph.get("simplified"):
            show_toast(self, f"记忆节点较多，已简化显示前 100 个（共 {graph['total']} 个）")

    def _create_edge_item(self, edge: dict[str, Any]) -> None:
        src = self.node_items.get(edge["source_node_id"])
        dst = self.node_items.get(edge["target_node_id"])
        if src and dst and src is not dst:
            line = QGraphicsLineItem()
            line.setPen(QPen(QColor(theme.current().border_light), 1.5))
            self.scene.addItem(line)
            self.edge_items.append((edge, line))

    def update_edges(self) -> None:
        for edge, line in self.edge_items:
            src = self.node_items.get(edge["source_node_id"])
            dst = self.node_items.get(edge["target_node_id"])
            if src and dst:
                # 线从端口位置到目标节点中心
                start = src.mapToScene(src.anchor.pos())
                line.setLine(start.x(), start.y(), dst.pos().x(), dst.pos().y())

    def persist_node(self, node_id: str, pos: QPointF) -> None:
        self.db.update_memory_node(node_id, x=pos.x(), y=pos.y())

    # ------------------------------------------------------------------ 临时连线（组装关系）
    def start_temp_edge(self, src: NodeItem, scene_pos: QPointF) -> None:
        self._temp_src = src
        green = QColor("#7dd0a0")
        pen = QPen(green, 2.5, Qt.PenStyle.DashLine)
        self._temp_edge = QGraphicsLineItem()
        self._temp_edge.setPen(pen)
        self._temp_edge.setZValue(1000)
        self.scene.addItem(self._temp_edge)
        self.update_temp_edge(scene_pos)

    def update_temp_edge(self, scene_pos: QPointF) -> None:
        if self._temp_edge and self._temp_src:
            start = self._temp_src.mapToScene(self._temp_src.anchor.pos())
            self._temp_edge.setLine(start.x(), start.y(), scene_pos.x(), scene_pos.y())

    def finish_temp_edge(self, src: NodeItem, scene_pos: QPointF) -> None:
        if self._temp_edge:
            self.scene.removeItem(self._temp_edge)
            self._temp_edge = None
        self._temp_src = None
        if not self.space_id:
            return
        # 命中目标节点
        target_item = None
        for item in self.scene.items(scene_pos):
            if isinstance(item, NodeItem) and item is not src:
                target_item = item
                break
        if target_item is None:
            return
        # 若已存在同向关系则不重复添加
        target_id = target_item.node_id
        if any(
            e[0]["source_node_id"] == src.node_id and e[0]["target_node_id"] == target_id
            for e in self.edge_items
        ):
            show_toast(self, "这两个节点已有连线")
            return
        edge = self.db.add_memory_edge(self.space_id, src.node_id, target_id, "related")
        self._create_edge_item(edge)
        self.update_edges()
        show_toast(self, "已建立节点关系")

    # ------------------------------------------------------------------ 缩放/平移
    def zoom_in(self) -> None:
        self.view.scale(1.25, 1.25)

    def zoom_out(self) -> None:
        self.view.scale(0.8, 0.8)

    def fit_view(self) -> None:
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

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

    # ------------------------------------------------------------------ 记忆拼图
    def selected_node_ids(self) -> list[str]:
        return [item.node_id for item in self.node_items.values() if item.isSelected()]

    def merge_selected(self) -> None:
        if not self.space_id:
            show_toast(self, "请先选择空间", success=False)
            return
        ids = self.selected_node_ids()
        if len(ids) < 2:
            show_toast(self, "请先用框选或按住 Ctrl 选择至少 2 个节点", success=False)
            return
        new_node = memory.merge_nodes(self.db, self.space_id, ids)
        if new_node:
            self.refresh()
            show_toast(self, f"已把 {len(ids)} 个节点拼合并成一个节点")
        else:
            show_toast(self, "合并失败", success=False)

    def summarize_selected(self) -> None:
        if not self.space_id:
            show_toast(self, "请先选择空间", success=False)
            return
        ids = self.selected_node_ids()
        if len(ids) < 2:
            show_toast(self, "请先选择至少 2 个节点", success=False)
            return
        texts = [
            memory.node_text(self.db.get_memory_node(node_id))
            for node_id in ids
            if self.db.get_memory_node(node_id)
        ]
        texts = [t for t in texts if t]
        if not texts:
            show_toast(self, "所选节点没有可总结的内容", success=False)
            return
        show_toast(self, "正在生成总结，请稍候…")
        self._sum_thread = SummarizeThread(texts)
        self._sum_thread.done.connect(self._on_summary_done)
        self._sum_ids = ids
        self._sum_thread.start()

    def _on_summary_done(self, result: str) -> None:
        if not self.space_id:
            return
        if result.startswith("总结失败"):
            show_toast(self, result, success=False)
            return
        memory.summarize_nodes(self.db, self.space_id, self._sum_ids, result)
        self.refresh()
        show_toast(self, "已生成 AI 总结记忆节点")