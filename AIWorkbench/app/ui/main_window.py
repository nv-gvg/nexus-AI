"""主窗口：拼装所有面板、菜单、快捷键、系统托盘与更新检查。"""

from __future__ import annotations

import json
from datetime import datetime

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QSystemTrayIcon,
    QTabWidget,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from .. import backup, paths
from ..config import get_config
from ..logger import get_logger
from ..workers import UpdateCheckThread
from .about_dialog import AboutDialog
from .config_dialog import ConfigDialog
from .conversation_view import ChatView, ConversationListView
from .graph_view import GraphView
from .skill_panel import SkillPanel
from .space_panel import SpacePanel
from .widgets import show_toast


def _make_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor("#1565c0"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setPointSize(24)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "AI")
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, db, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.config = get_config()
        self.log = get_logger()

        self.setWindowTitle(f"{paths.APP_NAME} v{paths.APP_VERSION}")
        self.setWindowIcon(_make_icon())
        self.resize(1280, 780)

        self._build_panels()
        self._build_menu()
        self._build_shortcuts()
        self._build_tray()

        # 初始刷新
        self.space_panel.refresh()

    # ------------------------------------------------------------------ 布局
    def _build_panels(self) -> None:
        self.space_panel = SpacePanel(self.db)
        self.conversation_list = ConversationListView(self.db)
        self.chat_view = ChatView(self.db)
        self.graph_view = GraphView(self.db)
        self.skill_panel = SkillPanel()

        right_tabs = QTabWidget()
        right_tabs.addTab(self.graph_view, "记忆图谱")
        right_tabs.addTab(self.skill_panel, "技能")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.space_panel)
        splitter.addWidget(self.conversation_list)
        splitter.addWidget(self.chat_view)
        splitter.addWidget(right_tabs)
        splitter.setSizes([180, 240, 560, 320])
        splitter.setStretchFactor(2, 1)
        self.setCentralWidget(splitter)

        # 信号
        self.space_panel.space_changed.connect(self._on_space_changed)
        self.space_panel.space_created.connect(self._on_spaces_changed)
        self.space_panel.space_deleted.connect(self._on_space_deleted)
        self.conversation_list.conversation_selected.connect(self._on_conversation_selected)
        self.conversation_list.conversation_created_signal.connect(self._on_conversation_created)
        self.chat_view.conversation_created.connect(self._on_chat_created_conversation)
        self.chat_view.graph_refresh_requested.connect(self.graph_view.refresh)
        self.graph_view.node_clicked.connect(self._on_node_clicked)

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("导出单个空间…", self.export_space)
        file_menu.addAction("导入空间…", self.import_space)
        file_menu.addSeparator()
        file_menu.addAction("整体备份 (ZIP)…", self.export_all)
        file_menu.addAction("整体恢复 (ZIP)…", self.import_all)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.quit_app)

        space_menu = menubar.addMenu("空间(&S)")
        space_menu.addAction("新建空间", QKeySequence("Ctrl+N"), self.new_space)
        space_menu.addAction("新建对话", QKeySequence("Ctrl+Shift+N"), self.new_conversation)

        edit_menu = menubar.addMenu("编辑(&E)")
        edit_menu.addAction("保存/导出当前对话", QKeySequence("Ctrl+S"), self.save_conversation)
        edit_menu.addAction("搜索当前对话", QKeySequence("Ctrl+F"), self.search_current)
        edit_menu.addAction("全局搜索", QKeySequence("Ctrl+Shift+F"), self.search_global)
        edit_menu.addAction("打开配置面板", QKeySequence("Ctrl+,"), self.open_config)

        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("关于", self.show_about)

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Esc"), self, activated=self._on_escape)

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(_make_icon(), self)
        tray_menu = QMenu()
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_main_window)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(
            lambda reason: self.show_main_window()
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick
            else None
        )
        self.tray.show()
        self._really_quit = False
        self._tray_notified = False

    # ------------------------------------------------------------------ 事件处理
    def _on_space_changed(self, space_id: str) -> None:
        self.conversation_list.refresh(space_id)
        self.chat_view.set_space(space_id)
        self.graph_view.set_space(space_id)

    def _on_spaces_changed(self) -> None:
        pass

    def _on_space_deleted(self) -> None:
        self.conversation_list.refresh("")
        self.chat_view.set_space(None)
        self.graph_view.set_space(None)

    def _on_conversation_selected(self, conversation_id: str) -> None:
        space_id = self.space_panel.current_space_id
        if space_id:
            self.chat_view.load_conversation(space_id, conversation_id)

    def _on_conversation_created(self) -> None:
        space_id = self.space_panel.current_space_id
        if space_id:
            self.conversation_list.refresh(space_id)

    def _on_chat_created_conversation(self) -> None:
        space_id = self.space_panel.current_space_id
        if space_id:
            self.conversation_list.refresh(space_id, self.chat_view.conversation_id)

    def _on_node_clicked(self, node: dict) -> None:
        source = ""
        conv = None
        # 溯源
        msg_id = node.get("source_message_id")
        if msg_id:
            rows = self.db._query(
                "SELECT conversation_id FROM messages WHERE id = ?", (msg_id,)
            )
            if rows:
                conv = self.db.get_conversation(rows[0]["conversation_id"])
                source = conv["title"] if conv else ""
        meta = node.get("metadata", {}) or {}
        detail = (
            f"标签: {node.get('label', '')}\n"
            f"类型: {node.get('type', '？')}\n"
            f"来源对话: {source or '无'}\n"
            f"记忆内容: {meta.get('memory', '')}\n"
            f"创建时间: {node.get('created_at', '')}"
        )
        QMessageBox.information(self, "节点详情", detail)

    # ------------------------------------------------------------------ 动作
    def new_space(self) -> None:
        self.space_panel.create_space()

    def new_conversation(self) -> None:
        space_id = self.space_panel.current_space_id
        if not space_id:
            show_toast(self, "请先选择空间", success=False)
            return
        conv = self.db.create_conversation(space_id, "新对话")
        self.conversation_list.refresh(space_id, conv["id"])
        self.chat_view.load_conversation(space_id, conv["id"])

    def save_conversation(self) -> None:
        conv_id = self.chat_view.conversation_id
        if not conv_id:
            show_toast(self, "请先选择对话", success=False)
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出对话", "conversation.json", "JSON (*.json)")
        if path:
            data = self.db.list_messages(conv_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            show_toast(self, "对话已导出")

    def open_config(self) -> None:
        dialog = ConfigDialog(self)
        dialog.exec()

    def show_about(self) -> None:
        AboutDialog(self).exec()

    def export_space(self) -> None:
        space_id = self.space_panel.current_space_id
        if not space_id:
            show_toast(self, "请先选择空间", success=False)
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出空间", "space.json", "JSON (*.json)")
        if path:
            backup.export_space(self.db, space_id, path)
            show_toast(self, "空间已导出")

    def import_space(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入空间", "", "JSON (*.json)")
        if path:
            backup.import_space(self.db, path)
            self.space_panel.refresh()
            show_toast(self, "空间已导入")

    def export_all(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "整体备份", "aiworkbench_backup.zip", "ZIP (*.zip)")
        if path:
            backup.export_all(self.db, path)
            show_toast(self, "整体备份完成")

    def import_all(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "整体恢复", "", "ZIP (*.zip)")
        if path:
            n = backup.import_all(self.db, path)
            self.space_panel.refresh()
            show_toast(self, f"已恢复 {n} 个空间")

    # ------------------------------------------------------------------ 搜索
    def search_current(self) -> None:
        conv_id = self.chat_view.conversation_id
        if not conv_id:
            show_toast(self, "请先选择对话", success=False)
            return
        kw, ok = QInputDialog.getText(self, "搜索当前对话", "关键词:")
        if not ok or not kw:
            return
        results = [
            m for m in self.db.list_messages(conv_id) if kw in m["content"]
        ]
        self._show_search_results("当前对话搜索结果", [f"[{m['role']}] {m['content']}" for m in results])

    def search_global(self) -> None:
        kw, ok = QInputDialog.getText(self, "全局搜索", "关键词:")
        if not ok or not kw:
            return
        results = self.db.global_search(kw)
        lines = [
            f"[{m['space_name']} | {m['conversation_title']} | {m['role']}] {m['content']}"
            for m in results
        ]
        self._show_search_results("全局搜索结果", lines)

    def _show_search_results(self, title: str, lines: list[str]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(640, 400)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n\n".join(lines) if lines else "没有匹配结果")
        layout.addWidget(text)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    # ------------------------------------------------------------------ 托盘/关闭
    def _on_escape(self) -> None:
        if self.chat_view.streaming:
            self.chat_view.stop_generation()
        else:
            # 关闭可能打开的模态对话框由 Qt 处理，这里聚焦输入框
            self.chat_view.input.setFocus()

    def show_main_window(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def quit_app(self) -> None:
        self._really_quit = True
        self.tray.hide()
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.config.get("close_to_tray", True) and not self._really_quit:
            event.ignore()
            self.hide()
            if not self._tray_notified:
                self.tray.showMessage(
                    paths.APP_NAME, "已最小化到系统托盘", QSystemTrayIcon.MessageIcon.Information, 2000
                )
                self._tray_notified = True
        else:
            event.accept()

    # ------------------------------------------------------------------ 更新检查
    def check_updates(self) -> None:
        if not self.config.get("check_updates", True):
            return
        self.update_thread = UpdateCheckThread(self)
        self.update_thread.finished.connect(self._on_update_result)
        self.update_thread.start()

    def _on_update_result(self, result) -> None:
        if not result:
            return
        box = QMessageBox(self)
        box.setWindowTitle("发现新版本")
        box.setText(f"新版本 {result.get('tag', '')} 已发布。")
        box.setInformativeText(result.get("body", "")[:300])
        download_btn = box.addButton("前往下载", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("忽略", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == download_btn:
            QDesktopServices.openUrl(QUrl(result.get("html_url", paths.GITHUB_REPO)))