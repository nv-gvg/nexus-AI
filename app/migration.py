"""数据迁移：旧版本配置/数据自动迁移到新版本格式。"""

from __future__ import annotations

from .config import get_config
from .logger import get_logger

# 下次升级示例：如果已有 schema_version=1 的旧表结构，在此补充迁移步骤。

MIGRATIONS: dict[int, callable] = {}


def run_migrations() -> None:
    """检测并执行迁移。当前版本为初始版本，暂无迁移步骤。"""
    log = get_logger()
    config = get_config()
    current = int(config.get("version", 1))

    for version in sorted(MIGRATIONS):
        if current < version:
            log.info("检测到旧版数据，正在迁移到 v%s", version)
            MIGRATIONS[version]()
            config.set("version", version)

    # 确保版本号始终为最新
    if int(config.get("version", 1)) < 1:
        config.set("version", 1)