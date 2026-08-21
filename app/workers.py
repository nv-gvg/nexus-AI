"""后台线程：AI 流式调用与更新检查。"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from .api_client import APIClient
from .config import get_config
from .mcp_client import MCPClient
from . import updater


class ChatThread(QThread):
    """在一个后台线程中执行流式请求，避免阻塞 UI。"""

    token_ready = pyqtSignal(str)
    succeeded = pyqtSignal(str)   # 完整回复文本
    failed = pyqtSignal(str)      # 错误信息

    def __init__(self, client: APIClient, messages: list[dict[str, str]], system_extra: str = "", parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.messages = messages
        self.system_extra = system_extra
        self._stop = False

    def run(self) -> None:
        try:
            mcp_client = None
            servers = get_config().get_mcp_servers()
            if servers:
                mcp_client = MCPClient(servers)
            full = self.client.stream_chat(
                self.messages,
                on_token=lambda token: self.token_ready.emit(token),
                should_stop=lambda: self._stop,
                system_extra=self.system_extra,
                mcp_client=mcp_client,
            )
            self.succeeded.emit(full)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))

    def stop(self) -> None:
        self._stop = True


class UpdateCheckThread(QThread):
    """启动时静默检查更新。"""

    finished = pyqtSignal(object)  # None 或 dict(版本信息)

    def run(self) -> None:
        self.finished.emit(updater.check_and_compare())