"""配置面板：API Key（加密）、Base URL、模型、采样参数、系统提示。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..config import get_config
from .widgets import show_toast


class ConfigDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.config = get_config()
        self.setWindowTitle("配置")
        self.setMinimumWidth(520)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.base_url_edit = QLineEdit()
        form.addRow("Base URL:", self.base_url_edit)

        self.model_edit = QLineEdit()
        form.addRow("模型名称:", self.model_edit)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        form.addRow("Temperature:", self.temperature_spin)

        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        form.addRow("Top P:", self.top_p_spin)

        layout.addLayout(form)

        layout.addWidget(QLabel("System Prompt:"))
        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setFixedHeight(90)
        layout.addWidget(self.system_prompt_edit)

        # MCP 服务器
        layout.addWidget(QLabel("MCP 服务器（让 AI 调用外部工具）:"))
        self.mcp_list = QListWidget()
        self.mcp_list.setMaximumHeight(80)
        layout.addWidget(self.mcp_list)

        mcp_row = QHBoxLayout()
        add_mcp_btn = QPushButton("添加 MCP 服务器")
        add_mcp_btn.clicked.connect(self._add_mcp)
        remove_mcp_btn = QPushButton("删除所选")
        remove_mcp_btn.clicked.connect(self._remove_mcp)
        mcp_row.addWidget(add_mcp_btn)
        mcp_row.addWidget(remove_mcp_btn)
        mcp_row.addStretch(1)
        layout.addLayout(mcp_row)

        # API Keys
        layout.addWidget(QLabel("API Keys（加密存储，自动轮换）:"))
        self.keys_list = QListWidget()
        layout.addWidget(self.keys_list)

        keys_row = QHBoxLayout()
        add_btn = QPushButton("添加 Key")
        add_btn.clicked.connect(self._add_key)
        remove_btn = QPushButton("删除所选 Key")
        remove_btn.clicked.connect(self._remove_key)
        keys_row.addWidget(add_btn)
        keys_row.addWidget(remove_btn)
        keys_row.addStretch(1)
        layout.addLayout(keys_row)

        actions = QHBoxLayout()
        reset_btn = QPushButton("重置配置")
        reset_btn.clicked.connect(self._reset)
        save_btn = QPushButton("保存")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(reset_btn)
        actions.addStretch(1)
        actions.addWidget(cancel_btn)
        actions.addWidget(save_btn)
        layout.addLayout(actions)

    def _load(self) -> None:
        self.base_url_edit.setText(self.config.get("base_url", ""))
        self.model_edit.setText(self.config.get("model", ""))
        self.temperature_spin.setValue(float(self.config.get("temperature", 0.7)))
        self.top_p_spin.setValue(float(self.config.get("top_p", 1.0)))
        self.system_prompt_edit.setPlainText(self.config.get("system_prompt", ""))
        self._mcp_servers = list(self.config.get_mcp_servers())
        self._refresh_keys()
        self._refresh_mcp()

    def _refresh_keys(self) -> None:
        self.keys_list.clear()
        for key in self.config.get_api_keys():
            masked = self._mask(key)
            self.keys_list.addItem(masked)

    @staticmethod
    def _mask(key: str) -> str:
        if len(key) <= 8:
            return "****"
        return f"{key[:6]}...{key[-4:]}"

    def _add_key(self) -> None:
        key, ok = QInputDialog.getText(self, "添加 API Key", "API Key:", QLineEdit.EchoMode.Password)
        if ok and key.strip():
            self.config.add_api_key(key.strip())
            self._refresh_keys()

    def _remove_key(self) -> None:
        row = self.keys_list.currentRow()
        if row >= 0:
            self.config.remove_api_key(row)
            self._refresh_keys()

    def _refresh_mcp(self) -> None:
        self.mcp_list.clear()
        for s in self._mcp_servers:
            transport = s.get("transport", "stdio")
            target = s.get("url") if transport in ("sse", "http") else s.get("command", "")
            self.mcp_list.addItem(f"{s.get('name', '?')}  ({transport} → {target})")

    def _add_mcp(self) -> None:
        dlg = MCPServerDialog(self)
        if dlg.exec():
            self._mcp_servers.append(dlg.result_server())
            self._refresh_mcp()

    def _remove_mcp(self) -> None:
        row = self.mcp_list.currentRow()
        if 0 <= row < len(self._mcp_servers):
            del self._mcp_servers[row]
            self._refresh_mcp()

    def _save(self) -> None:
        self.config.update(
            {
                "base_url": self.base_url_edit.text().strip(),
                "model": self.model_edit.text().strip(),
                "temperature": self.temperature_spin.value(),
                "top_p": self.top_p_spin.value(),
                "system_prompt": self.system_prompt_edit.toPlainText(),
            }
        )
        self.config.set_mcp_servers(self._mcp_servers)
        show_toast(self, "配置已保存，立即生效")
        self.accept()

    def _reset(self) -> None:
        ret = QMessageBox.question(self, "重置配置", "确定恢复默认配置吗？API Key 将被清空。")
        if ret == QMessageBox.StandardButton.Yes:
            self.config.reset()
            self._load()
            show_toast(self, "已重置配置")


class MCPServerDialog(QDialog):
    """新增 MCP 服务器的简单表单。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("添加 MCP 服务器")
        form = QFormLayout(self)

        self.name_edit = QLineEdit()
        form.addRow("名称:", self.name_edit)

        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["stdio", "sse"])
        form.addRow("传输方式:", self.transport_combo)

        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("例如 python / npx / node")
        form.addRow("命令 (stdio):", self.command_edit)

        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("用逗号分隔，例如 mcp_server.py,C:/data")
        form.addRow("参数 (逗号分隔):", self.args_edit)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/mcp")
        form.addRow("URL (sse):", self.url_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def result_server(self) -> dict:
        args = [a.strip() for a in self.args_edit.text().split(",") if a.strip()]
        return {
            "name": self.name_edit.text().strip() or "未命名",
            "transport": self.transport_combo.currentText(),
            "command": self.command_edit.text().strip(),
            "args": args,
            "url": self.url_edit.text().strip(),
            "enabled": True,
        }