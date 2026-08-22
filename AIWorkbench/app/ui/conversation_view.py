"""对话区：对话列表 + 聊天视图。"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtGui import QGuiApplication, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStackedLayout,
)

from .. import memory
from ..api_client import APIClient, estimate_tokens
from ..config import get_config
from ..skills import SkillManager
from ..workers import ChatThread
from .mobius import render_infinity_background
from .widgets import JumpingDots, MessageWidget, show_toast


class InfinityBackground(QWidget):
    """半透明无限符号背景装饰层。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._bg_pixmap: QPixmap | None = None
        self._generating = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._generating:
            return
        w, h = self.width(), self.height()
        if w > 0 and h > 0:
            self._generating = True
            try:
                self._bg_pixmap = render_infinity_background(w, h)
                self.update()
            except Exception:
                pass
            finally:
                self._generating = False

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._bg_pixmap:
            painter = QPainter(self)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                target_w = int(self.width() * 0.85)
                target_h = int(self.height() * 0.85)
                scaled = self._bg_pixmap.scaled(
                    target_w, target_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            finally:
                painter.end()


class ConversationListView(QWidget):
    """当前空间的对话列表。"""

    conversation_selected = pyqtSignal(str)
    conversation_created_signal = pyqtSignal()

    def __init__(self, db, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.space_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("\u25a0  \u5bf9\u8bdd")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_changed)
        layout.addWidget(self.list_widget)

        new_btn = QPushButton("＋ 新建对话")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self.new_conversation)
        layout.addWidget(new_btn)

    def refresh(self, space_id: str, select_id: str | None = None) -> None:
        self.space_id = space_id
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for conv in self.db.list_conversations(space_id):
            item = QListWidgetItem(conv["title"])
            item.setData(Qt.ItemDataRole.UserRole, conv["id"])
            self.list_widget.addItem(item)
            if select_id and conv["id"] == select_id:
                self.list_widget.setCurrentItem(item)
        self.list_widget.blockSignals(False)

        if self.list_widget.count() == 0:
            empty = QListWidgetItem("还没有对话")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            empty.setForeground(Qt.GlobalColor.gray)
            self.list_widget.addItem(empty)

    def _on_changed(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        conv_id = current.data(Qt.ItemDataRole.UserRole)
        if conv_id:
            self.conversation_selected.emit(conv_id)

    def new_conversation(self) -> None:
        if not self.space_id:
            return
        conv = self.db.create_conversation(self.space_id, "新对话")
        self.refresh(self.space_id, conv["id"])
        self.conversation_created_signal.emit()

    def rename_item(self, conv_id: str, title: str) -> None:
        self.db.rename_conversation(conv_id, title)
        if self.space_id:
            self.refresh(self.space_id, conv_id)


class ChatView(QWidget):
    """聊天主区域。"""

    conversation_created = pyqtSignal()          # 通知主窗口刷新对话列表
    graph_refresh_requested = pyqtSignal()       # 记忆变化后刷新图谱
    title_changed = pyqtSignal(str, str)         # (conv_id, title)

    def __init__(self, db, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.config = get_config()
        self.client = APIClient()
        self.skill_manager = SkillManager()

        self.space_id: str | None = None
        self.conversation_id: str | None = None
        self.streaming = False
        self.thread: ChatThread | None = None
        self.stream_widget: MessageWidget | None = None

        self._build_ui()
        self.show_empty_state("请选择一个空间和对话开始")
        # 延迟同步背景大小
        QTimer.singleShot(100, self._sync_infinity_bg)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶部：标题 + token 用量 + 生成指示
        top = QHBoxLayout()
        top.setContentsMargins(12, 8, 12, 8)
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        top.addWidget(self.title_label)
        top.addStretch(1)
        self.gen_dots = JumpingDots()
        self.gen_dots.setVisible(False)
        top.addWidget(self.gen_dots)
        self.token_label = QLabel("Tokens: 0")
        self.token_label.setStyleSheet("color: #7c828c; font-size: 12px;")
        top.addWidget(self.token_label)
        self.memory_btn = QPushButton("保存记忆")
        self.memory_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.memory_btn.clicked.connect(self.save_current_memory)
        top.addWidget(self.memory_btn)
        layout.addLayout(top)

        # 消息区域容器（包含无限符号背景）
        self.msg_area = QWidget()
        msg_area_layout = QVBoxLayout(self.msg_area)
        msg_area_layout.setContentsMargins(0, 0, 0, 0)
        msg_area_layout.setSpacing(0)

        # 无限符号背景层
        self.infinity_bg = InfinityBackground(self.msg_area)
        self.infinity_bg.setGeometry(self.msg_area.rect())
        self.infinity_bg.lower()

        # 消息滚动区
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("QWidget { background: transparent; }")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(12, 8, 12, 8)
        self.msg_layout.setSpacing(10)
        self.msg_layout.addStretch(1)
        self.scroll.setWidget(self.msg_container)

        msg_area_layout.addWidget(self.scroll)
        layout.addWidget(self.msg_area, 1)

        # 输入区
        input_box = QWidget()
        input_layout = QVBoxLayout(input_box)
        input_layout.setContentsMargins(12, 4, 12, 8)

        self.input = QTextEdit()
        self.input.setPlaceholderText("输入消息，Shift+Enter 换行，Enter 发送")
        self.input.setFixedHeight(92)
        self.input.installEventFilter(self)
        input_layout.addWidget(self.input)

        btn_row = QHBoxLayout()
        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        btn_row.addWidget(self.hint_label)
        btn_row.addStretch(1)
        self.send_btn = QPushButton("发送")
        self.send_btn.setObjectName("accentBtn")
        self.send_btn.setFixedWidth(90)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self.on_send_clicked)
        btn_row.addWidget(self.send_btn)
        input_layout.addLayout(btn_row)

        layout.addWidget(input_box)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_infinity_bg()

    def _sync_infinity_bg(self) -> None:
        """同步无限符号背景层的大小。"""
        if hasattr(self, 'infinity_bg') and hasattr(self, 'msg_area'):
            self.infinity_bg.setGeometry(self.msg_area.rect())
            self.infinity_bg.lower()

    # ------------------------------------------------------------------ 空状态/加载
    def show_empty_state(self, text: str) -> None:
        self._clear_messages()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #8b92a0; font-size: 15px;")
        self.msg_layout.insertWidget(0, label)
        self._empty_label = label

    def _clear_messages(self) -> None:
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def set_space(self, space_id: str | None) -> None:
        self.space_id = space_id
        self.conversation_id = None
        self.title_label.setText("")
        self.update_token_usage()
        self.show_empty_state("还没有对话，开始你的第一条消息吧")

    def load_conversation(self, space_id: str, conversation_id: str) -> None:
        self.set_space(space_id)
        self.conversation_id = conversation_id
        conv = self.db.get_conversation(conversation_id)
        if conv:
            self.title_label.setText(conv["title"])
        self._clear_messages()
        msgs = self.db.list_messages(conversation_id)
        if not msgs:
            self.show_empty_state("还没有对话，开始你的第一条消息吧")
        else:
            for m in msgs:
                self._append_message_widget(m)
            self.update_token_usage()
        self._scroll_to_bottom()

    # ------------------------------------------------------------------ 消息渲染
    def _append_message_widget(self, msg: dict) -> MessageWidget:
        w = MessageWidget(msg["id"], msg["role"], msg["content"], msg["created_at"])
        w.copy_requested.connect(self._copy_message)
        w.delete_requested.connect(self._delete_message)
        w.edit_requested.connect(self._edit_message)
        w.memory_requested.connect(self._attach_memory_to_message)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, w)
        return w

    def _scroll_to_bottom(self) -> None:
        def _do():
            bar = self.scroll.verticalScrollBar()
            bar.setValue(bar.maximum())
        QTimer.singleShot(0, _do)

    def update_token_usage(self) -> None:
        total = estimate_tokens(self.config.get("system_prompt", ""))
        if self.conversation_id:
            for m in self.db.list_messages(self.conversation_id):
                total += estimate_tokens(m["content"])
        self.token_label.setText(f"Tokens: {total}")

    # ------------------------------------------------------------------ 发送
    def on_send_clicked(self) -> None:
        if self.streaming:
            self.stop_generation()
        else:
            self.send_message()

    def send_message(self) -> None:
        if self.streaming:
            return
        text = self.input.toPlainText().strip()
        if not text:
            return
        if not self.space_id:
            show_toast(self, "请先选择一个空间", success=False)
            return

        if not self.conversation_id:
            conv = self.db.create_conversation(self.space_id, text[:20] or "新对话")
            self.conversation_id = conv["id"]
            self.title_label.setText(conv["title"])
            self.conversation_created.emit()
            self._clear_messages()

        # 技能注入 @技能名
        cleaned, injected = self.skill_manager.resolve_mentions(
            text, set(self.config.enabled_skills())
        )
        system_extra = injected

        # 保存用户消息
        user_msg = self.db.add_message(self.conversation_id, "user", text)
        self._append_message_widget(user_msg)
        self.input.clear()
        self.input.setFocus()
        self.update_token_usage()

        # 组装历史（不含 system，system 由客户端补充）
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in self.db.list_messages(self.conversation_id)
        ]

        self._start_stream(history, system_extra)

    def _start_stream(self, history: list[dict[str, str]], system_extra: str) -> None:
        self.streaming = True
        self.send_btn.setText("停止")
        self.send_btn.setObjectName("dangerBtn")
        self.send_btn.style().unpolish(self.send_btn)
        self.send_btn.style().polish(self.send_btn)
        self.gen_dots.setVisible(True)

        # 占位 assistant 气泡
        placeholder = {
            "id": "__streaming__",
            "role": "assistant",
            "content": "",
            "created_at": "",
        }
        self.stream_widget = self._append_message_widget(placeholder)
        self.stream_widget.start_typing_cursor()
        self._scroll_to_bottom()

        self.thread = ChatThread(self.client, history, system_extra, self)
        self.thread.token_ready.connect(self._on_token)
        self.thread.succeeded.connect(self._on_stream_done)
        self.thread.failed.connect(self._on_stream_failed)
        self.thread.start()

    def _on_token(self, token: str) -> None:
        if self.stream_widget:
            self.stream_widget.append_text(token)
            self._scroll_to_bottom()

    def _on_stream_done(self, full_text: str) -> None:
        self._finish_stream(full_text, error=None)

    def _on_stream_failed(self, err: str) -> None:
        self._finish_stream(None, error=err)

    def _finish_stream(self, full_text: str | None, error: str | None) -> None:
        self.streaming = False
        self.gen_dots.setVisible(False)
        self.send_btn.setText("发送")
        self.send_btn.setObjectName("accentBtn")
        self.send_btn.style().unpolish(self.send_btn)
        self.send_btn.style().polish(self.send_btn)
        self.thread = None

        if self.stream_widget:
            self.stream_widget.stop_typing_cursor()
        has_content = bool(self.stream_widget and self.stream_widget.content().strip())

        if full_text is not None:
            if self.conversation_id:
                saved = self.db.add_message(self.conversation_id, "assistant", full_text)
                if self.stream_widget:
                    self.stream_widget.message_id = saved["id"]
        elif has_content:
            # 部分内容也保存
            content = self.stream_widget.content()
            if self.conversation_id:
                saved = self.db.add_message(self.conversation_id, "assistant", content)
                if self.stream_widget:
                    self.stream_widget.message_id = saved["id"]
        else:
            # 无内容且失败，移除占位
            if self.stream_widget:
                self.msg_layout.removeWidget(self.stream_widget)
                self.stream_widget.deleteLater()

        self.stream_widget = None
        self.update_token_usage()

        if error:
            show_toast(self, f"调用失败: {error}", success=False)
            err_label = QLabel(f"错误: {error}")
            err_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            self.msg_layout.insertWidget(self.msg_layout.count() - 1, err_label)
            self._scroll_to_bottom()

    def stop_generation(self) -> None:
        if self.thread:
            self.thread.stop()
        # 让线程自然结束会触发 _finish_stream（via succeeded)，这里不做强杀
        show_toast(self, "正在停止生成...", success=True)

    # ------------------------------------------------------------------ 重新生成
    def regenerate(self) -> None:
        """重新生成最后一条 assistant 消息。"""
        if self.streaming or not self.conversation_id:
            return
        msgs = self.db.list_messages(self.conversation_id)
        if not msgs:
            return
        # 移除最后一条 assistant（若存在）
        if msgs[-1]["role"] == "assistant":
            self.db.delete_message(msgs[-1]["id"])
            self._clear_messages()
            for m in self.db.list_messages(self.conversation_id):
                self._append_message_widget(m)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in self.db.list_messages(self.conversation_id)
        ]
        self._start_stream(history, "")

    # ------------------------------------------------------------------ 消息操作
    def _copy_message(self, message_id: str) -> None:
        content = self._find_content(message_id)
        if content:
            QGuiApplication.clipboard().setText(content)
            show_toast(self, "已复制到剪贴板")

    def _delete_message(self, message_id: str) -> None:
        self.db.delete_message(message_id)
        self.load_conversation(self.space_id, self.conversation_id)
        show_toast(self, "已删除消息")

    def _edit_message(self, message_id: str) -> None:
        content = self._find_content(message_id)
        if content:
            self.input.setPlainText(content)
            self.input.setFocus()

    def _find_content(self, message_id: str) -> str:
        for m in self.db.list_messages(self.conversation_id or ""):
            if m["id"] == message_id:
                return m["content"]
        return ""

    def _attach_memory_to_message(self, message_id: str) -> None:
        if not self.space_id:
            return
        text, ok = QInputDialog.getMultiLineText(self, "挂载记忆", "为这条消息写一段记忆:")
        if ok and text.strip():
            memory.attach_memory_to_message(self.db, self.space_id, message_id, text.strip())
            show_toast(self, "记忆已保存")
            self.graph_refresh_requested.emit()

    def save_current_memory(self) -> None:
        """把当前对话最后一条消息挂载为记忆（快捷入口）。"""
        if not self.conversation_id:
            show_toast(self, "请先选择对话", success=False)
            return
        msgs = self.db.list_messages(self.conversation_id)
        if not msgs:
            show_toast(self, "还没有可保存的消息", success=False)
            return
        self._attach_memory_to_message(msgs[-1]["id"])

    # ------------------------------------------------------------------ 键盘
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return False  # 换行
                self.send_message()
                return True
        return super().eventFilter(obj, event)