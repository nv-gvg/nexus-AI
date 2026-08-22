"""配置管理。

- 使用 cryptography 的 Fernet 加密存储 API Key。
- 配置文件为 data 根目录下的 config.json。
- 修改后立即生效（所有读取方每次都从本对象取最新值）。
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from . import paths
from .logger import get_logger

_DEFAULTS: dict[str, Any] = {
    "version": 1,
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "top_p": 1.0,
    "system_prompt": "你是一个乐于助人的智能助手。",
    "current_key_index": 0,
    "close_to_tray": True,
    "check_updates": True,
    "setup_completed": False,
    # 界面主题："dark"（深色）或 "light"（浅色）
    "theme": "dark",
    # 外部插件市场地址（JSON 数组；留空则使用内置目录）
    "market_url": "",
    "enabled_skills": [],
    # 下载/导出目录（为空时使用系统“文档”目录）
    "download_dir": "",
    # MCP 服务器列表（每项含 name/transport/command/args/url）
    "mcp_servers": [],
    # 加密后的 API Key 列表（base64 字符串）
    "api_keys_encrypted": [],
}


def builtin_mcp_servers() -> list[dict[str, Any]]:
    """内置 MCP 服务器：把本地记忆/图谱以 MCP 工具形式开放给自己的客户端。

    仅在源码运行时可用（打包成 exe 后无独立 python 解释器运行 mcp_server.py）。
    """
    if paths.is_frozen():
        return []
    return [
        {
            "name": "本地记忆",
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(paths.resource_path("mcp_server.py"))],
            "enabled": True,
            "builtin": True,
        }
    ]


class Config:
    """线程安全的配置读写，API Key 加密存储。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._fernet: Fernet | None = None
        self._path = paths.config_path()
        self.log = get_logger()
        self._load_key()
        self.load()

    # ------------------------------------------------------------------ 密钥
    def _load_key(self) -> None:
        kp = paths.key_path()
        if kp.exists():
            self._fernet = Fernet(kp.read_bytes())
        else:
            self._fernet = None

    def _ensure_key_file(self) -> None:
        if self._fernet is None:
            kp = paths.key_path()
            kp.parent.mkdir(parents=True, exist_ok=True)
            if kp.exists():
                self._fernet = Fernet(kp.read_bytes())
            else:
                kp.write_bytes(Fernet.generate_key())
                self._fernet = Fernet(kp.read_bytes())

    @property
    def _cipher(self) -> Fernet:
        self._ensure_key_file()
        return self._fernet  # type: ignore[return-value]

    # ------------------------------------------------------------------ 加载/保存
    def load(self) -> None:
        with self._lock:
            if self._path.exists():
                try:
                    raw = json.loads(self._path.read_text(encoding="utf-8"))
                    self._data = dict(_DEFAULTS)
                    self._data.update(raw)
                except (json.JSONDecodeError, OSError) as exc:
                    self.log.warning("读取配置失败，使用默认配置: %s", exc)
                    self._data = dict(_DEFAULTS)
            else:
                self._data = dict(_DEFAULTS)
                self.save()

    def save(self) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp.replace(self._path)

    # ------------------------------------------------------------------ 通用访问
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self.save()

    def update(self, mapping: dict[str, Any]) -> None:
        with self._lock:
            self._data.update(mapping)
            self.save()

    def all(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    # ------------------------------------------------------------------ 加密
    def encrypt(self, plaintext: str) -> str:
        return self._cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            return ""

    # ------------------------------------------------------------------ API Key 轮换
    def add_api_key(self, key: str) -> None:
        if not key.strip():
            return
        enc = self.encrypt(key.strip())
        with self._lock:
            keys = list(self._data.get("api_keys_encrypted", []))
            keys.append(enc)
            self._data["api_keys_encrypted"] = keys
            self.save()

    def get_api_keys(self) -> list[str]:
        with self._lock:
            return [self.decrypt(e) for e in self._data.get("api_keys_encrypted", [])]

    def next_api_key(self) -> str | None:
        """轮换：返回下一个 Key（按 current_key_index 递增），无 Key 返回 None。"""
        keys = self.get_api_keys()
        if not keys:
            return None
        with self._lock:
            idx = int(self._data.get("current_key_index", 0)) % len(keys)
            self._data["current_key_index"] = (idx + 1) % len(keys)
            self.save()
        return keys[idx]

    def remove_api_key(self, index: int) -> None:
        with self._lock:
            keys = list(self._data.get("api_keys_encrypted", []))
            if 0 <= index < len(keys):
                del keys[index]
                self._data["api_keys_encrypted"] = keys
                self.save()

    # ------------------------------------------------------------------ 技能启用状态
    def enable_skill(self, name: str) -> None:
        with self._lock:
            enabled = list(self._data.get("enabled_skills", []))
            if name not in enabled:
                enabled.append(name)
                self._data["enabled_skills"] = enabled
                self.save()

    def disable_skill(self, name: str) -> None:
        with self._lock:
            enabled = list(self._data.get("enabled_skills", []))
            if name in enabled:
                enabled.remove(name)
                self._data["enabled_skills"] = enabled
                self.save()

    def enabled_skills(self) -> list[str]:
        with self._lock:
            return list(self._data.get("enabled_skills", []))

    # ------------------------------------------------------------------ 下载/导出目录
    def download_dir(self) -> str:
        """返回下载/导出目录。未设置时使用系统的“下载/文档”目录。"""
        with self._lock:
            configured = self._data.get("download_dir", "")
        if configured:
            return configured
        docs = Path.home() / "Documents"
        return str(docs if docs.exists() else Path.home())

    def set_download_dir(self, directory: str) -> None:
        with self._lock:
            self._data["download_dir"] = (directory or "").strip()
            self.save()

    # ------------------------------------------------------------------ MCP 服务器
    def get_mcp_servers(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._data.get("mcp_servers", []))

    def set_mcp_servers(self, servers: list[dict[str, Any]]) -> None:
        with self._lock:
            self._data["mcp_servers"] = servers
            self.save()

    def all_mcp_servers(self) -> list[dict[str, Any]]:
        """内置 + 用户自定义的全部 MCP 服务器。"""
        return builtin_mcp_servers() + self.get_mcp_servers()

    # ------------------------------------------------------------------ 重置
    def reset(self) -> None:
        with self._lock:
            self._data = dict(_DEFAULTS)
            self.save()


_config_instance: Config | None = None


def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance