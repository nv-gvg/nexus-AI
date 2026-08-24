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
from ..skills import market_catalog, SkillManager
from . import theme
from .widgets import show_toast


class SkillPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panelRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
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
        market_btn = QPushButton("插件市场")
        market_btn.clicked.connect(self.open_market)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        for b in (install_btn, uninstall_btn, market_btn, refresh_btn):
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

    # ------------------------------------------------------------------ 插件市场
    def open_market(self) -> None:
        from PyQt6.QtCore import QThread, pyqtSignal
        from PyQt6.QtWidgets import (
            QDialog,
            QLineEdit,
            QListWidget,
        )
        from ..skills import fetch_remote_market, install_market_plugin, market_catalog

        class _FetchThread(QThread):
            done = pyqtSignal(object)  # list | None

            def __init__(self, url: str) -> None:
                super().__init__()
                self.url = url

            def run(self) -> None:
                self.done.emit(fetch_remote_market(self.url))

        installed = {s.name for s in self.manager.list_skills()}

        dialog = QDialog(self)
        dialog.setWindowTitle("插件市场")
        dialog.resize(600, 520)
        layout = QVBoxLayout(dialog)

        # 市场源地址（外部 JSON 目录，可自定义）
        url_row = QHBoxLayout()
        url_label = QLabel("市场地址:")
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("外部插件市场 JSON 地址，留空使用内置目录")
        url_edit.setText(self.config.get("market_url", ""))
        url_row.addWidget(url_label)
        url_row.addWidget(url_edit, 1)
        layout.addLayout(url_row)

        hint = QLabel("正在加载插件目录…")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{theme.current().text_dim};")
        layout.addWidget(hint)

        market_list = QListWidget()
        layout.addWidget(market_list, 1)

        def render(catalog: list[dict]) -> None:
            market_list.clear()
            for spec in catalog:
                name = spec["name"]
                state = "（已安装）" if name in installed else ""
                src = "外部" if spec.get("source") == "remote" else "内置"
                market_list.addItem(
                    f"[{src}] {name}  v{spec['version']}  {state}\n    {spec['description']}"
                )

        def load(catalog: list[dict]) -> None:
            # 外部 + 内置兜底合并展示
            remote = [s for s in catalog if s.get("source") == "remote"]
            builtin = [dict(s) for s in market_catalog() if s["name"] not in {x["name"] for x in remote}]
            merged = remote + builtin
            if remote:
                hint.setText(f"已加载外部市场（{len(remote)} 个插件）+ 内置目录（{len(builtin)} 个）")
            else:
                hint.setText("无法连接外部市场，已回退到内置目录。请检查「市场地址」后点击加载。")
            render(merged)
            dialog._market_specs = merged

        def do_fetch() -> None:
            url = url_edit.text().strip()
            self.config.set("market_url", url)
            hint.setText("正在加载外部插件市场…")
            market_list.clear()
            t = _FetchThread(url)
            t.done.connect(lambda catalog: load(catalog if catalog is not None else []))
            t.start()

        # 打开时自动尝试加载外部市场（无地址则直接显示内置）
        if url_edit.text().strip():
            do_fetch()
        else:
            load([])

        load_btn = QPushButton("加载外部市场")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(do_fetch)
        install_btn = QPushButton("安装所选插件")
        install_btn.setObjectName("accentBtn")
        install_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def do_install() -> None:
            row = market_list.currentRow()
            if row < 0:
                show_toast(dialog, "请先选择一个插件", success=False)
                return
            specs = getattr(dialog, "_market_specs", [])
            if row >= len(specs):
                return
            spec = specs[row]
            if spec["name"] in installed:
                show_toast(dialog, "该插件已安装", success=False)
                return
            try:
                install_market_plugin(spec)
                show_toast(dialog, f"已安装插件「{spec['name']}」，重启后在输入框 @名字 调用")
                installed.add(spec["name"])
                render(specs)
            except Exception as exc:  # noqa: BLE001
                show_toast(dialog, f"安装失败: {exc}", success=False)
        install_btn.clicked.connect(do_install)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        btn_row = QHBoxLayout()
        btn_row.addWidget(load_btn)
        btn_row.addWidget(install_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        dialog.exec()
        self.refresh()