"""路径与常量定义。

所有用户数据统一存放在: %USERPROFILE%\\Documents\\AIWorkbench\\
    data\\      数据库
    backups\\   每日备份
    logs\\      日志
    skills\\    技能包
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "AIWorkbench"
APP_VERSION = "0.1.0"
APP_LICENSE = "Apache-2.0"
GITHUB_REPO = "https://github.com/yourname/AIWorkbench"  # 请替换为你的仓库地址
GITHUB_API = "https://api.github.com/repos/yourname/AIWorkbench"  # 请替换


def _default_root() -> Path:
    docs = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(docs) / "Documents" / APP_NAME


def get_data_root() -> Path:
    """返回数据根目录，支持通过环境变量覆盖（测试/便携模式）。"""
    override = os.environ.get("AIWORKBENCH_DATA_DIR")
    return Path(override) if override else _default_root()


def data_dir() -> Path:
    return get_data_root() / "data"


def backups_dir() -> Path:
    return get_data_root() / "backups"


def logs_dir() -> Path:
    return get_data_root() / "logs"


def skills_dir() -> Path:
    return get_data_root() / "skills"


def db_path() -> Path:
    return data_dir() / "aiworkbench.db"


def config_path() -> Path:
    return get_data_root() / "config.json"


def key_path() -> Path:
    return data_dir() / ".secret.key"


def ensure_dirs() -> Path:
    """创建所有需要的目录，返回数据根目录。"""
    root = get_data_root()
    for d in (data_dir(), backups_dir(), logs_dir(), skills_dir()):
        d.mkdir(parents=True, exist_ok=True)
    return root


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包后的环境中。"""
    return getattr(sys, "frozen", False)


def resource_path(relative: str) -> Path:
    """获取打包后仍可用的资源路径。"""
    if is_frozen():
        return Path(sys._MEIPASS) / relative  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / relative