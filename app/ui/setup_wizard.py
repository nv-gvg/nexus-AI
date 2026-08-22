"""首次启动配置向导。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
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
        self.setWindowTitle("欢迎使用 AIWorkbench")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.welcome_page = self._welcome_page()
        self.data_page = self._data_page()
        self.key_page = self._key_page()
        self.model_page = self._model_page()

        self.addPage(self.welcome_page)
        self.addPage(self.data_page)
        self.addPage(self.key_page)
        self.addPage(self.model_page)

    def _welcome_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("欢迎")
        layout = QVBoxLayout(page)
        label = QLabel(
            "AIWorkbench 是一个本地优先的开源 AI 工作台。\n\n"
            "你可以创建多个独立空间，每个空间拥有独立的对话、\n"
            "知识图谱记忆和配置。"
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        return page

    def _data_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("数据目录")
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("你的数据将存储在以下位置（首次启动自动创建）："))
        dir_label = QLabel(str(paths.get_data_root()))
        dir_label.setStyleSheet("font-weight: bold; color: #7b8cff;")
        dir_label.setWordWrap(True)
        layout.addWidget(dir_label)
        layout.addWidget(QLabel("数据仅存储在本地，不会上传到你的机器之外。"))
        return page

    def _key_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("API Key")
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("填写你的 API Key（支持 OpenAI 兼容接口）："))
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_edit)
        layout.addWidget(QLabel("可留空，稍后在配置面板中填写。"))
        return page

    def _model_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("默认模型")
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("选择默认模型，或直接输入自定义模型名："))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(COMMON_MODELS)
        self.model_combo.setCurrentText("gpt-4o-mini")
        layout.addWidget(self.model_combo)
        return page

    def accept(self) -> None:
        key = self.key_edit.text().strip()
        if key:
            self.config.add_api_key(key)
        self.config.set("model", self.model_combo.currentText().strip())
        self.config.set("setup_completed", True)
        super().accept()