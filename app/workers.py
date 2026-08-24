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
            servers = get_config().all_mcp_servers()
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


class AutoMemoryThread(QThread):
    """后台调用 AI 把最近几轮对话自动总结成一条记忆节点。

    触发：由调用方在每轮对话完成后检查 should_auto_summarize，满足则启动本线程。
    """

    done = pyqtSignal(object)   # 新记忆节点 dict 或 None
    failed = pyqtSignal(str)    # 错误信息

    def __init__(self, db, space_id: str, material: str, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.space_id = space_id
        self.material = material

    def run(self) -> None:
        from .api_client import APIClient
        from . import memory

        prompt = (
            "你在为一位用户维护长期记忆。请阅读下面最近几轮对话，"
            "提取值得长期记住的关键信息（用户的目标、偏好、重要事实、决策等），"
            "整理成 3-5 条简洁的中文要点，不要复述对话过程，不要客套。\n\n"
            + self.material
        )
        try:
            summary = APIClient().chat_text([{"role": "user", "content": prompt}])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        node = memory.save_auto_summary(self.db, self.space_id, summary)
        self.done.emit(node)


class UpdateCheckThread(QThread):
    """启动时静默检查更新。"""

    finished = pyqtSignal(object)  # None 或 dict(版本信息)

    def run(self) -> None:
        self.finished.emit(updater.check_and_compare())