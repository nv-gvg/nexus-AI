"""首次启动配置向导。

三项均为可选，不会强制拦截用户：
    1) 欢迎页；
    2) 目录设置（数据目录展示 + 下载/导出目录自定义）；
    3) 接入 AI（API Key 与模型均可留空，稍后在配置面板再填）。

注意：不使用 QWizard.ModernStyle（它有硬编码的深色标题栏和按钮栏），
改为在每个 QWizardPage 上自绘标题，配合 QSS 实现深浅主题一致外观。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
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
from . import theme

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


def _make_title(text: str) -> QLabel:
    """创建页面大标题（随主题自适应深色/浅色）。"""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: 22px; font-weight: bold; color: {theme.current().text_bright};"
    )
    return lbl


def _make_separator() -> QFrame:
    """标题下的分隔线。"""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    line.setStyleSheet(f"background: {theme.current().border}; max-height: 1px;")
    return line


def _body_label(text: str) -> QLabel:
    """正文标签，深色文字确保浅色模式下清晰可读。"""
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color: {theme.current().text}; font-size: 14px;")
    return lbl


class SetupWizard(QWizard):
    def __init__(self, config=None, parent=None) -> None:
        super().__init__(parent)
        self.config = config or get_config()
        self.setWindowTitle("欢迎使用 Nexus-AI")
        # 不使用 ModernStyle（其硬编码深色 banner 无法被 QSS 覆盖）
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOptions(
            QWizard.WizardOption.IndependentPages
            | QWizard.WizardOption.NoBackButtonOnStartPage
            | QWizard.WizardOption.HaveHelpButton
        )
        # 移除帮助按钮
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.setMinimumSize(560, 440)

        self.addPage(self._welcome_page())
        self.addPage(self._dirs_page())
        self.addPage(self._ai_page())

        # 按钮文字中文化
        self.setButtonText(QWizard.WizardButton.NextButton, "下一步 >")
        self.setButtonText(QWizard.WizardButton.BackButton, "< 上一步")
        self.setButtonText(QWizard.WizardButton.FinishButton, "完成")
        self.setButtonText(QWizard.WizardButton.CancelButton, "取消")

    def _welcome_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(12)

        layout.addWidget(_make_title("欢迎使用 Nexus-AI"))
        layout.addWidget(_make_separator())
        layout.addSpacing(8)

        text = _body_label(
            "Nexus-AI 是一个本地优先的开源 AI 工作台。\n\n"
            "你可以创建多个独立「空间」，每个空间拥有独立的对话、"
            "知识图谱记忆和配置。\n\n"
            "接下来几步都是可选的——你随时可以跳过，稍后在设置里再补。"
        )
        text.setStyleSheet(
            f"color: {theme.current().text}; font-size: 14px; line-height: 1.6;"
        )
        layout.addWidget(text)
        layout.addStretch(1)
        return page

    def _dirs_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(10)

        layout.addWidget(_make_title("目录设置"))
        layout.addWidget(_make_separator())
        layout.addSpacing(6)

        data_title = _body_label("数据目录（仅本地存储，不会上传）：")
        data_title.setStyleSheet(
            f"color: {theme.current().text}; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(data_title)

        dir_label = QLabel(str(paths.get_data_root()))
        dir_label.setStyleSheet(
            f"color: {theme.current().accent}; font-size: 13px; "
            f"background: {theme.current().accent_glow}; "
            f"border: 1px solid {theme.current().accent_dark}; "
            f"border-radius: {theme.current().radius_sm}px; "
            f"padding: 8px 12px;"
        )
        dir_label.setWordWrap(True)
        layout.addWidget(dir_label)
        layout.addSpacing(12)

        dl_title = _body_label("下载 / 导出目录（对话、空间、备份保存的位置）：")
        dl_title.setStyleSheet(
            f"color: {theme.current().text}; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(dl_title)

        row = QHBoxLayout()
        self.download_edit = QLineEdit()
        self.download_edit.setPlaceholderText("请选择目录（例如 D:\\Downloads）")
        row.addWidget(self.download_edit, 1)
        browse_btn = QPushButton("选择…")
        browse_btn.clicked.connect(self._browse_download)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        hint = _body_label("默认使用系统文档目录；点击「选择…」即可自定义到任意盘符。")
        hint.setStyleSheet(f"color: {theme.current().text_dim}; font-size: 12px;")
        layout.addWidget(hint)
        layout.addStretch(1)
        return page

    def _ai_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(10)

        layout.addWidget(_make_title("接入 AI（可选）"))
        layout.addWidget(_make_separator())
        layout.addSpacing(6)

        self.skip_ai = QCheckBox("暂不接入 AI，稍后在配置面板中设置")
        self.skip_ai.setStyleSheet(f"color: {theme.current().text}; font-size: 13px;")
        layout.addWidget(self.skip_ai)
        layout.addSpacing(8)

        key_label = _body_label("API Key（留空则跳过）:")
        key_label.setStyleSheet(f"color: {theme.current().text}; font-size: 13px;")
        layout.addWidget(key_label)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_edit)
        layout.addSpacing(6)

        model_label = _body_label("默认模型（留空则保持默认）:")
        model_label.setStyleSheet(f"color: {theme.current().text}; font-size: 13px;")
        layout.addWidget(model_label)
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
        start = self.download_edit.text().strip()
        if not start:
            start = str(Path.home() / "Desktop")
        folder = QFileDialog.getExistingDirectory(self, "选择下载/导出目录", start)
        if folder:
            self.download_edit.setText(folder)

    def accept(self) -> None:
        self.config.set_download_dir(self.download_edit.text().strip())
        if not self.skip_ai.isChecked():
            key = self.key_edit.text().strip()
            if key:
                self.config.add_api_key(key)
            model = self.model_combo.currentText().strip()
            if model:
                self.config.set("model", model)
        self.config.set("setup_completed", True)
        super().accept()
