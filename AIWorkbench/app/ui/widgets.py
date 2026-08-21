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

def show_toast(parent: QWidget, text: str, success: bool = True, duration_ms: int = 2500) -> None:
    """在父窗口右下角显示提示条。"""
    toast = Toast(parent, text, success)
    toast.show()
    QTimer.singleShot(duration_ms, toast.close)


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
            dot.setStyleSheet("color: #888; font-size: 14px;")
            layout.addWidget(dot)
            self._dots.append(dot)
        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(300)

    def _tick(self) -> None:
        for i, dot in enumerate(self._dots):
            active = (i == self._step)
            dot.setStyleSheet(f"color: {'#333' if active else '#ccc'}; font-size: 14px;")
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

        is_user = role == "user"
        bg = "#e3f2fd" if is_user else "#ffffff"
        align = Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft

        self.setObjectName("messageWidget")
        self.setStyleSheet(
            f"#messageWidget {{ background: {bg}; border: 1px solid #e0e0e0;"
            " border-radius: 8px; }}"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(6)

        header = QHBoxLayout()
        role_label = QLabel("你" if is_user else "AI")
        role_label.setStyleSheet(
            f"font-weight: bold; color: {'#1565c0' if is_user else '#2e7d32'};"
        )
        header.addWidget(role_label)
        header.addStretch(1)
        time_label = QLabel(created_at)
        time_label.setStyleSheet("color: #999; font-size: 11px;")
        header.addWidget(time_label)
        outer.addLayout(header)

        self.content_label = QLabel(content)
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.content_label.setStyleSheet("color: #222; font-size: 14px;")
        self.content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        outer.addWidget(self.content_label)

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
        if is_user:
            edit_btn = QPushButton("编辑")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.message_id))
            btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        outer.addLayout(btn_row)

        self._outer_align_wrapper = None

    def append_text(self, delta: str) -> None:
        self.content_label.setText(self.content_label.text() + delta)

    def set_content(self, text: str) -> None:
        self.content_label.setText(text)

    def content(self) -> str:
        return self.content_label.text()