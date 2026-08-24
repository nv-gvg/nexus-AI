"""数据迁移：旧版本配置/数据自动迁移到新版本格式。"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import paths
from .config import get_config
from .logger import get_logger

# 下次升级示例：如果已有 schema_version=1 的旧表结构，在此补充迁移步骤。

MIGRATIONS: dict[int, callable] = {}


def _migrate_from_documents() -> None:
    """v0.2.0 起把数据根从 Documents 迁到 AppData\\Roaming。

    若 AppData 下还没有 aiworkbench.db，但 Documents 下有旧数据，
    则把整个旧数据目录整体拷贝到 AppData，保留原位置不删。
    """
    log = get_logger()
    new_root = paths.get_data_root()
    new_db = new_root / "data" / "aiworkbench.db"
    if new_db.exists():
        return

    userprofile = Path.home()
    old_root = userprofile / "Documents" / paths.APP_NAME
    if not old_root.exists():
        return

    log.info("检测到旧版数据目录，从 %s 迁移到 %s", old_root, new_root)
    new_root.parent.mkdir(parents=True, exist_ok=True)
    if new_root.exists():
        return
    try:
        shutil.copytree(old_root, new_root, dirs_exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("迁移旧数据失败（可忽略）：%s", exc)


def run_migrations() -> None:
    """检测并执行迁移。"""
    log = get_logger()
    config = get_config()

    _migrate_from_documents()

    current = int(config.get("version", 1))

    for version in sorted(MIGRATIONS):
        if current < version:
            log.info("检测到旧版数据，正在迁移到 v%s", version)
            MIGRATIONS[version]()
            config.set("version", version)

    if int(config.get("version", 1)) < 1:
        config.set("version", 1)