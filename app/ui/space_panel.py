"""空间面板：左侧空间列表，支持新建/删除/重命名/切换。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SpacePanel(QWidget):
    space_changed = pyqtSignal(str)          # 当前空间 id
    space_created = pyqtSignal()
    space_deleted = pyqtSignal()

    def __init__(self, db, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.db = db
        self.current_space_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("\u25a0  \u7a7a\u95f4")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("新建")
        new_btn.clicked.connect(self.create_space)
        rename_btn = QPushButton("重命名")
        rename_btn.clicked.connect(self.rename_space)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.delete_space)
        for b in (new_btn, rename_btn, del_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

    def refresh(self, select_id: str | None = None) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for space in self.db.list_spaces():
            item = QListWidgetItem(space["name"])
            item.setData(Qt.ItemDataRole.UserRole, space["id"])
            self.list_widget.addItem(item)
            if select_id and space["id"] == select_id:
                self.list_widget.setCurrentItem(item)
        self.list_widget.blockSignals(False)

        # 空状态
        if self.list_widget.count() == 0:
            empty = QListWidgetItem("创建第一个空间")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            empty.setForeground(Qt.GlobalColor.gray)
            self.list_widget.addItem(empty)

        if select_id is None and self.list_widget.count() > 0:
            first_real = None
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.ItemDataRole.UserRole):
                    first_real = self.list_widget.item(i)
                    break
            if first_real and self.list_widget.currentItem() is None:
                self.list_widget.setCurrentItem(first_real)

    def _on_item_changed(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        space_id = current.data(Qt.ItemDataRole.UserRole)
        if space_id:
            self.current_space_id = space_id
            self.space_changed.emit(space_id)

    def create_space(self) -> None:
        name, ok = QInputDialog.getText(self, "新建空间", "空间名称:")
        if ok and name.strip():
            space = self.db.create_space(name.strip())
            self.refresh(space["id"])
            self.space_created.emit()

    def rename_space(self) -> None:
        if not self.current_space_id:
            return
        name, ok = QInputDialog.getText(self, "重命名空间", "新名称:")
        if ok and name.strip():
            self.db.rename_space(self.current_space_id, name.strip())
            self.refresh(self.current_space_id)
            self.space_created.emit()

    def delete_space(self) -> None:
        if not self.current_space_id:
            return
        ret = QMessageBox.question(
            self, "删除空间", "确定删除该空间及其所有对话和记忆吗？此操作不可撤销。"
        )
        if ret == QMessageBox.StandardButton.Yes:
            self.db.delete_space(self.current_space_id)
            self.current_space_id = None
            self.refresh()
            self.space_deleted.emit()