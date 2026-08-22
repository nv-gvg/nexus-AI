"""AIWorkbench 启动入口。

用法:
    python main.py            # 正常启动（首次运行会进入配置向导）
    python main.py --reset    # 重置本地配置（开发/排障用）
"""

import sys
import os


def ensure_package_path() -> None:
    """打包为 exe 后资源路径可能与源码不同，这里保证包可导入。"""
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)


def main() -> int:
    ensure_package_path()

    from app import create_application

    app = create_application()
    window = app.main_window
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())