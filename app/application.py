"""应用装配：初始化目录、日志、配置、数据库，创建主窗口和向导。"""

from __future__ import annotations

import os
import sys

from . import backup, migration, paths, skills
from .config import get_config
from .database import Database
from .logger import setup_logger


def _acquire_single_instance():
    """通过命名互斥量实现单实例保护（进程退出自动释放）。

    返回 (is_first, handle)。is_first=False 表示已有实例在运行。
    在 PyInstaller 单文件模式下，命名互斥量比 QSharedMemory 更可靠。
    """
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        handle = kernel32.CreateMutexW(None, False, "Global\\Nexus-AI-SingleInstance")
        if handle and ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.kernel32.CloseHandle(handle)
            return False, None
        return True, handle
    return True, None


def _install_global_exception_hooks() -> None:
    """在崩溃退出前把未捕获异常写入日志，便于诊断「保存设置后退出」类问题。

    - sys.excepthook：捕获主线程未处理异常。
    - faulthandler：捕获 C++/原生段错误（Access Violation）类闪退。
    """
    from .logger import get_logger

    def _hook(exc_type, exc, tb) -> None:
        import traceback

        try:
            log = get_logger()
            log.critical("未捕获异常（应用即将退出）: %s", exc)
            log.critical("".join(traceback.format_exception(exc_type, exc, tb)))
            # 双通道：同时尝试写一份独立崩溃日志到 exe 同级，方便查找
            try:
                crash_dir = paths.get_data_root()
                crash_dir.mkdir(parents=True, exist_ok=True)
                crash_file = crash_dir / "crash.log"
                with crash_file.open("a", encoding="utf-8") as f:
                    f.write("\n==== crash at %s ====\n" % paths.APP_NAME)
                    traceback.print_exception(exc_type, exc, tb, file=f)
            except Exception:  # noqa: BLE001
                pass
        finally:
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook

    # 原生崩溃（如 Qt C++ ABI 崩溃/越界）也会闪退，注册到独立文件
    try:
        import faulthandler

        crash_dir = paths.get_data_root()
        crash_dir.mkdir(parents=True, exist_ok=True)
        faulthandler.enable(file=(crash_dir / "crash.log").open("a", encoding="utf-8"), all_threads=True)
    except Exception:  # noqa: BLE001
        pass


def create_application():
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QMessageBox

    from .ui import theme
    from .ui.main_window import MainWindow
    from .ui.setup_wizard import SetupWizard

    # 0. 全局异常钩子：崩溃退出前留下 traceback
    _install_global_exception_hooks()

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

    # 6.5 单实例保护：防止重复启动导致多个窗口/托盘图标
    is_first, guard = _acquire_single_instance()
    if not is_first:
        QMessageBox.information(None, paths.APP_NAME, f"{paths.APP_NAME} 已在运行中。")
        return None
    app._single_instance_guard = guard  # 持有互斥量句柄，进程退出时自动释放

    theme.apply_theme(app, light=config.get("theme", "dark") == "light")

    # 7. 主窗口
    window = MainWindow(db)
    app.main_window = window

    # 8. 首次启动配置向导（强制浅色，不要黑底）
    if not config.get("setup_completed", False):
        theme.apply_theme(app, light=True)
        wizard = SetupWizard(config)
        wizard.exec()
        # 向导关闭后恢复用户配置的主题
        cfg_light = config.get("theme", "dark") == "light"
        theme.apply_theme(app, light=cfg_light)

    # 9. 检查更新（延迟，避免阻塞启动）
    QTimer.singleShot(1500, window.check_updates)

    return app