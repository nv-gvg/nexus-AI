"""更新检查：启动时检查 GitHub Releases 是否有新版本。"""

from __future__ import annotations

import re
from typing import Any

import requests

from . import paths
from .logger import get_logger


def _normalize(version: str) -> tuple[int, ...]:
    digits = re.findall(r"\d+", version)
    return tuple(int(d) for d in digits) or (0,)


def is_newer(latest: str, current: str) -> bool:
    return _normalize(latest) > _normalize(current)


def check_latest_version(api_url: str | None = None) -> dict[str, Any] | None:
    """查询 GitHub Latest Release。失败返回 None（不强制更新）。"""
    api = api_url or paths.GITHUB_API
    if "yourname" in api:
        # 占位仓库未配置，跳过检查
        return None

    log = get_logger()
    try:
        resp = requests.get(
            f"{api}/releases/latest",
            headers={"Accept": "application/vnd.github+json"},
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return {
            "tag": data.get("tag_name", ""),
            "name": data.get("name", ""),
            "html_url": data.get("html_url", ""),
            "body": data.get("body", ""),
        }
    except requests.RequestException as exc:
        log.debug("检查更新失败: %s", exc)
        return None


def check_and_compare() -> dict[str, Any] | None:
    """返回需要提示更新的信息；若无新版本返回 None。"""
    latest = check_latest_version()
    if not latest:
        return None
    if is_newer(latest.get("tag", ""), paths.APP_VERSION):
        return latest
    return None