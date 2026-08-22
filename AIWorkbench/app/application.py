"""应用装配：初始化目录、日志、配置、数据库，创建主窗口和向导。"""

from __future__ import annotations

import sys

from . import backup, migration, paths, skills
from .config import get_config
from .database import Database
from .logger import setup_logger


def create_application():
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from .ui import theme
    from .ui.main_window import MainWindow
    from .ui.setup_wizard import SetupWizard

    # 1. 目录与日志
    paths.ensure_dirs()
    log = setup_logger()
    log.info("启动 %s v%s", paths.APP_NAME, paths.APP_VERSION)

    # 2. 配置
    config = get_config()

    # 2.5 内置技能（首次自动安装并启用）
    skills.install_builtin_skills(config)

    # 3. 数据迁移
    migration.run_migrations()

    # 4. 数据库
    db = Database(paths.db_path())

    # 5. 每日备份
    backup.daily_backup(db)

    # 6. Qt 应用
    app = QApplication(sys.argv)
    app.setApplicationName(paths.APP_NAME)
    app.setApplicationVersion(paths.APP_VERSION)
    theme.apply_theme(app, light=config.get("theme", "dark") == "light")

    # 7. 主窗口
    window = MainWindow(db)
    app.main_window = window

    # 8. 首次启动配置向导
    if not config.get("setup_completed", False):
        wizard = SetupWizard(config)
        wizard.exec()

    # 9. 检查更新（延迟，避免阻塞启动）
    QTimer.singleShot(1500, window.check_updates)

    return app