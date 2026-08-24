"""路径与常量定义。

所有用户数据统一存放在: %USERPROFILE%\\Documents\\Nexus-AI\\
    data\\      数据库
    backups\\   每日备份
    logs\\      日志
    skills\\    技能包
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Nexus-AI"
APP_VERSION = "0.3.0"
APP_LICENSE = "Apache-2.0"
GITHUB_REPO = "https://github.com/NV-GVG/Nexus-AI"
GITHUB_API = "https://api.github.com/repos/NV-GVG/Nexus-AI"


def _default_root() -> Path:
    """按优先级选择第一个可写的应用数据根目录。

    优先级：
    1. exe 所在目录/当前工作目录（便携模式，最通用）
    2. APPDATA（%Roaming%）
    3. LOCALAPPDATA（%LocalAppData%）
    4. 用户主目录

    这样在受限环境（如沙盒）中会自动降级到可写目录。
    """
    candidates: list[Path] = []
    if is_frozen():
        candidates.append(Path(sys.executable).resolve().parent / APP_NAME)
    else:
        candidates.append(Path.cwd() / APP_NAME)
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / APP_NAME)
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / APP_NAME)
    candidates.append(Path.home() / APP_NAME)

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue
    return candidates[0]


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


def workflows_dir() -> Path:
    return get_data_root() / "workflows"


def db_path() -> Path:
    return data_dir() / "aiworkbench.db"


def config_path() -> Path:
    return get_data_root() / "config.json"


def key_path() -> Path:
    return data_dir() / ".secret.key"


def ensure_dirs() -> Path:
    """创建所有需要的目录，返回数据根目录。"""
    root = get_data_root()
    for d in (data_dir(), backups_dir(), logs_dir(), skills_dir(), workflows_dir()):
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