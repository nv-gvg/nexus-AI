"""深色主题：全局 QSS 样式表 + 装饰元素。"""

from __future__ import annotations

ACCENT = "#7b8cff"
ACCENT_DARK = "#5a66d6"
ACCENT_GLOW = "rgba(123, 140, 255, 0.15)"
BG = "#0e0f13"
BG_GRADIENT = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #11131a, stop:1 #0a0b0f)"
SURFACE = "#16181e"
SURFACE_2 = "#1d2028"
SURFACE_3 = "#222631"
BORDER = "#272c36"
BORDER_LIGHT = "#343b4a"
TEXT = "#e7e9ee"
TEXT_DIM = "#9aa1ad"
TEXT_BRIGHT = "#ffffff"

STYLE = f"""
/* ===== 全局 ===== */
QMainWindow, QDialog, QWizard, QMessageBox, QInputDialog {{
    background: {BG};
    color: {TEXT};
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QWidget {{
    background: transparent;
    color: {TEXT};
}}
QLabel {{
    background: transparent;
    color: {TEXT};
}}

/* ===== 顶栏 ===== */
QFrame#headerBar {{
    background: {BG_GRADIENT};
    border-bottom: 2px solid {ACCENT};
    border-bottom-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent,
        stop:0.15 {ACCENT},
        stop:0.50 {ACCENT_GLOW},
        stop:0.85 {ACCENT},
        stop:1 transparent);
}}
QFrame#headerBar::after {{
    background: {ACCENT_GLOW};
}}
QLabel#appName {{
    font-size: 18px;
    font-weight: bold;
    color: {TEXT_BRIGHT};
    letter-spacing: 1px;
}}
QLabel#appTagline {{
    font-size: 11px;
    color: {TEXT_DIM};
    letter-spacing: 0.5px;
}}
QLabel#versionBadge {{
    font-size: 10px;
    font-weight: bold;
    color: {ACCENT};
    background: {ACCENT_GLOW};
    border: 1px solid {ACCENT_DARK};
    border-radius: 8px;
    padding: 1px 8px;
}}

/* ===== 侧边栏面板 ===== */
QFrame#sidePanel {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
}}
QLabel#panelTitle {{
    font-size: 11px;
    font-weight: bold;
    color: {TEXT_DIM};
    letter-spacing: 1.5px;
    padding: 4px 0;
}}

/* ===== 按钮 ===== */
QPushButton {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 12px;
    min-height: 20px;
}}
QPushButton:hover {{
    background: {SURFACE_3};
    border-color: {BORDER_LIGHT};
}}
QPushButton:pressed {{
    background: #1b1f28;
}}
QPushButton:default {{
    background: {ACCENT_DARK};
    border-color: {ACCENT};
    color: white;
}}
QPushButton:disabled {{
    color: #5c626e;
    background: #14171d;
}}
QPushButton#accentBtn {{
    background: {ACCENT_DARK};
    color: white;
    border: 1px solid {ACCENT};
    border-radius: 6px;
    font-weight: bold;
}}
QPushButton#accentBtn:hover {{
    background: {ACCENT};
}}
QPushButton#iconBtn {{
    background: transparent;
    border: none;
    padding: 4px;
    font-size: 16px;
}}
QPushButton#iconBtn:hover {{
    background: {SURFACE_3};
    border-radius: 4px;
}}

/* ===== 输入框 ===== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {ACCENT_DARK};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
    background: {SURFACE_2};
}}

QComboBox {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
}}
QComboBox:hover {{ border-color: {BORDER_LIGHT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DARK};
}}

/* ===== 列表 ===== */
QListWidget, QTableWidget {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    alternate-background-color: {SURFACE_2};
}}
QListWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {BG}; }}
QListWidget::item:selected, QTableWidget::item:selected {{
    background: {ACCENT_DARK};
    color: white;
    border-left: 3px solid {ACCENT};
}}
QListWidget::item:hover {{ background: {SURFACE_2}; }}

QHeaderView::section {{
    background: {SURFACE_2};
    color: {TEXT_DIM};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 8px;
}}

/* ===== 标签页 ===== */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {SURFACE};
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_DIM};
    padding: 8px 18px;
    border-bottom: 2px solid transparent;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    color: {TEXT_BRIGHT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{ color: {TEXT}; }}

/* ===== 分割条 ===== */
QSplitter::handle {{
    background: {BORDER};
    width: 1px;
    height: 1px;
}}
QSplitter::handle:hover {{ background: {ACCENT_DARK}; }}

/* ===== 滚动条 ===== */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #2c3240;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #3a4152; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #2c3240;
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ===== 菜单栏 ===== */
QMenuBar {{
    background: {SURFACE};
    color: {TEXT};
    border-bottom: 1px solid {BORDER};
    padding: 2px;
}}
QMenuBar::item {{ padding: 6px 10px; border-radius: 4px; }}
QMenuBar::item:selected {{
    background: {SURFACE_3};
    border: 1px solid {BORDER_LIGHT};
}}
QMenu {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: {ACCENT_DARK}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

/* ===== 提示 ===== */
QToolTip {{
    background: {SURFACE_3};
    color: {TEXT};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 4px;
    padding: 4px 8px;
}}

QGraphicsView {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}

QSpinBox, QDoubleSpinBox {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 3px 6px;
}}

/* ===== 状态栏 ===== */
QStatusBar {{
    background: {SURFACE};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
    font-size: 11px;
}}
QStatusBar::item {{ border: none; }}
"""


def apply_theme(app) -> None:
    app.setStyleSheet(STYLE)