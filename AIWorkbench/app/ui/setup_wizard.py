"""首次启动配置向导。

三项均为可选，不会强制拦截用户：
    1) 数据目录展示（只读，说明数据存于本地）；
    2) 下载/导出目录（可自定义，不固定 C 盘）；
    3) 接入 AI（API Key 与模型均可留空，稍后在配置面板再填）。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from .. import paths
from ..config import get_config

COMMON_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1",
    "gpt-4.1-mini",
    "deepseek-chat",
    "deepseek-reasoner",
    "claude-3-5-sonnet",
    "qwen-max",
    "glm-4",
]


class SetupWizard(QWizard):
    def __init__(self, config=None, parent=None) -> None:
        super().__init__(parent)
        self.config = config or get_config()
        self.setWindowTitle("欢迎使用 Nexus-AI")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.addPage(self._welcome_page())
        self.addPage(self._dirs_page())
        self.addPage(self._ai_page())

    def _welcome_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("欢迎")
        layout = QVBoxLayout(page)
        label = QLabel(
            "Nexus-AI 是一个本地优先的开源 AI 工作台。\n\n"
            "你可以创建多个独立空间，每个空间拥有独立的对话、\n"
            "知识图谱记忆和配置。\n\n"
            "接下来几步都是可选的——你随时可以跳过，稍后在设置里再补。"
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        return page

    def _dirs_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("目录设置")
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("数据目录（仅本地存储，不会上传）："))
        dir_label = QLabel(str(paths.get_data_root()))
        dir_label.setStyleSheet("font-weight: bold; color: #7b8cff;")
        dir_label.setWordWrap(True)
        layout.addWidget(dir_label)
        layout.addSpacing(12)

        layout.addWidget(QLabel("下载 / 导出目录（对话、空间、备份保存的位置）："))
        row = QHBoxLayout()
        self.download_edit = QLineEdit()
        self.download_edit.setText(self.config.download_dir())
        row.addWidget(self.download_edit, 1)
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._browse_download)
        row.addWidget(browse_btn)
        layout.addLayout(row)
        layout.addWidget(QLabel("可以自定义到任意盘符，不再固定 C 盘。"))
        layout.addStretch(1)
        return page

    def _ai_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("接入 AI（可选）")
        layout = QVBoxLayout(page)

        self.skip_ai = QCheckBox("暂不接入 AI，稍后在配置面板中设置")
        layout.addWidget(self.skip_ai)

        layout.addWidget(QLabel("API Key（留空则跳过）:"))
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_edit)

        layout.addWidget(QLabel("默认模型（留空则保持默认）:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(COMMON_MODELS)
        self.model_combo.setCurrentText("")
        layout.addWidget(self.model_combo)

        self.skip_ai.toggled.connect(self._on_skip_toggled)
        layout.addStretch(1)
        return page

    def _on_skip_toggled(self, skipped: bool) -> None:
        for w in (self.key_edit, self.model_combo):
            w.setVisible(not skipped)
            w.setEnabled(not skipped)

    def _browse_download(self) -> None:
        start = self.download_edit.text().strip() or self.config.download_dir()
        folder = QFileDialog.getExistingDirectory(self, "选择下载/导出目录", start)
        if folder:
            self.download_edit.setText(folder)

    def accept(self) -> None:
        # 下载目录：无论是否改过都保存（自定义化，不再强制 C 盘默认）
        self.config.set_download_dir(self.download_edit.text().strip())
        # AI 接入：可跳过；不跳过时仅保存已填写的值
        if not self.skip_ai.isChecked():
            key = self.key_edit.text().strip()
            if key:
                self.config.add_api_key(key)
            model = self.model_combo.currentText().strip()
            if model:
                self.config.set("model", model)
        self.config.set("setup_completed", True)
        super().accept()