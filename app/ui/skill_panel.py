"""技能管理面板。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import get_config
from ..skills import SkillManager
from .widgets import show_toast


class SkillPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.manager = SkillManager()
        self.config = get_config()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("技能管理")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["名称", "版本", "描述", "启用"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        install_btn = QPushButton("安装技能包 (.skill)")
        install_btn.clicked.connect(self.install_skill)
        uninstall_btn = QPushButton("卸载所选")
        uninstall_btn.clicked.connect(self.uninstall_skill)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        for b in (install_btn, uninstall_btn, refresh_btn):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self.refresh()

    def refresh(self) -> None:
        skills = self.manager.list_skills()
        enabled = set(self.config.enabled_skills())
        self.table.setRowCount(len(skills))
        for row, skill in enumerate(skills):
            self.table.setItem(row, 0, QTableWidgetItem(skill.name))
            self.table.setItem(row, 1, QTableWidgetItem(skill.version))
            self.table.setItem(row, 2, QTableWidgetItem(skill.description))

            check = QTableWidgetItem("●" if skill.name in enabled else "○")
            check.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            check.setData(Qt.ItemDataRole.UserRole, skill.name)
            self.table.setItem(row, 3, check)

        self.table.cellClicked.connect(self.on_cell_clicked)

    def on_cell_clicked(self, row: int, col: int) -> None:
        if col != 3:
            return
        item = self.table.item(row, 3)
        name = item.data(Qt.ItemDataRole.UserRole)
        if not name:
            return
        if name in self.config.enabled_skills():
            self.config.disable_skill(name)
            show_toast(self, f"已禁用技能「{name}」")
        else:
            self.config.enable_skill(name)
            show_toast(self, f"已启用技能「{name}」")
        self.refresh()

    def install_skill(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择技能包", "", "技能包 (*.skill)")
        if not path:
            return
        try:
            self.manager.install(path)
            show_toast(self, "技能包安装成功")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            show_toast(self, f"安装失败: {exc}", success=False)

    def uninstall_skill(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            show_toast(self, "请先选择一个技能", success=False)
            return
        name_item = self.table.item(row, 0)
        if name_item:
            self.manager.uninstall(name_item.text())
            show_toast(self, "已卸载技能包")
            self.refresh()