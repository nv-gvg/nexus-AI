"""通用 UI 组件：提示条、跳动点、消息气泡。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme

def show_toast(parent: QWidget, text: str, success: bool = True, duration_ms: int = 2500) -> None:
    """在父窗口右下角显示提示条。

    注意：toast 使用自身持有的 QTimer 自动关闭并 deleteLater，
    避免依赖 QTimer.singleShot 的回调引用到可能会提前销毁的 parent。
    """
    toast = Toast(parent, text, success)
    toast.show()
    toast._timer = QTimer(toast)
    toast._timer.setSingleShot(True)
    toast._timer.timeout.connect(toast._auto_close)
    toast._timer.start(duration_ms)


class Toast(QLabel):
    def __init__(self, parent: QWidget, text: str, success: bool = True) -> None:
        super().__init__(parent)
        color = "#2e7d32" if success else "#c62828"
        self.setStyleSheet(
            f"QLabel {{ background-color: {color}; color: white; padding: 10px 16px;"
            " border-radius: 6px; font-size: 13px; }}"
        )
        self.setText(text)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.adjustSize()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        parent = self.parentWidget()
        if parent:
            x = parent.width() - self.width() - 24
            y = parent.height() - self.height() - 24
            self.move(x, y)

    def _auto_close(self) -> None:
        """由自身 QTimer 触发，安全关闭并回收，不担心 parent 已销毁。"""
        self.hide()
        self.deleteLater()


class JumpingDots(QWidget):
    """AI 回复时的跳动点动画。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        self._dots = []
        for _ in range(3):
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 14px;")
            layout.addWidget(dot)
            self._dots.append(dot)
        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(300)

    def _tick(self) -> None:
        for i, dot in enumerate(self._dots):
            active = (i == self._step)
            dot.setStyleSheet(
                f"color: {theme.ACCENT if active else theme.TEXT_DIM}; font-size: 14px;"
            )
        self._step = (self._step + 1) % 3

    def stop(self) -> None:
        self._timer.stop()


class MessageWidget(QFrame):
    """聊天消息气泡。"""

    copy_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    memory_requested = pyqtSignal(str)

    def __init__(self, message_id: str, role: str, content: str, created_at: str, parent=None) -> None:
        super().__init__(parent)
        self.message_id = message_id
        self.role = role
        self.created_at = created_at
        self._blink_on = False
        self._cursor_timer: QTimer | None = None
        self._is_user = role == "user"

        self.setObjectName("messageWidget")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(6)

        header = QHBoxLayout()
        self._role_label = QLabel("你" if self._is_user else "AI")
        header.addWidget(self._role_label)
        header.addStretch(1)
        self._time_label = QLabel(created_at)
        header.addWidget(self._time_label)
        outer.addLayout(header)

        self.content_label = QLabel(content)
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        outer.addWidget(self.content_label)
        self._content_label = self.content_label

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        copy_btn = QPushButton("复制")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(lambda: self.copy_requested.emit(self.message_id))
        mem_btn = QPushButton("记忆")
        mem_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mem_btn.clicked.connect(lambda: self.memory_requested.emit(self.message_id))
        del_btn = QPushButton("删除")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.message_id))
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(mem_btn)
        if self._is_user:
            edit_btn = QPushButton("编辑")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.message_id))
            btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        outer.addLayout(btn_row)

        self._outer_align_wrapper = None
        self._apply_theme()

    def _apply_theme(self) -> None:
        """按当前主题应用气泡配色（构造与换肤时调用）。"""
        is_user = self._is_user
        bubble_bg = theme.ACCENT_DARK if is_user else theme.SURFACE_2
        border = theme.ACCENT_DARK if is_user else theme.BORDER
        content_color = theme.TEXT_BRIGHT if is_user else theme.TEXT
        self._content_color = content_color
        self.setStyleSheet(
            f"#messageWidget {{ background: {bubble_bg}; border: 1px solid {border};"
            f" border-radius: 12px; }}"
        )
        self._role_label.setStyleSheet(
            f"font-weight: bold; color: {theme.ACCENT if is_user else theme.TEXT_GREEN};"
        )
        self._time_label.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 11px;")
        self._content_label.setStyleSheet(f"color: {content_color}; font-size: 14px;")

    def refresh_theme(self) -> None:
        """主题切换后刷新气泡颜色。"""
        self._apply_theme()

    def append_text(self, delta: str) -> None:
        text = self.content_label.text()
        cursor = "▋"
        if text.endswith(cursor):
            # 在闪烁光标前插入新内容，随后光标回到末尾
            self.content_label.setText(text[:-1] + delta + cursor)
        else:
            self.content_label.setText(text + delta)

    def set_content(self, text: str) -> None:
        self.content_label.setText(text)

    def content(self) -> str:
        return self.content_label.text()

    def start_typing_cursor(self) -> None:
        """显示流式输入的闪烁光标。"""
        if self._cursor_timer is None:
            self._cursor_timer = QTimer(self)
            self._cursor_timer.timeout.connect(self._blink)
            self._cursor_timer.start(400)
            self._blink(force_on=True)

    def stop_typing_cursor(self) -> None:
        """移除闪烁光标。"""
        if self._cursor_timer:
            self._cursor_timer.stop()
            self._cursor_timer = None
        self._update_cursor(False)

    def _blink(self, force_on: bool | None = None) -> None:
        if force_on is True:
            self._blink_on = True
        elif force_on is False:
            self._blink_on = False
        else:
            self._blink_on = not self._blink_on
        self._update_cursor(self._blink_on)

    def _update_cursor(self, visible: bool) -> None:
        text = self.content_label.text()
        cursor = "▋"
        if visible:
            if not text.endswith(cursor):
                self.content_label.setText(text + cursor)
        else:
            if text.endswith(cursor):
                self.content_label.setText(text[:-1])