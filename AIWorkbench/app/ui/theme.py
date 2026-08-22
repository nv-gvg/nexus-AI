"""主题系统：设计令牌 + 全局 QSS（深浅色自适应）。

所有颜色、圆角、间距都集中在这里，子模块通过 objectName 挂到
设计上下文中，保证全应用风格统一、可一键换肤。
"""

from __future__ import annotations


class Theme:
    """一套完整的设计令牌。"""

    def __init__(self, light: bool = False) -> None:
        self.light = light
        if light:
            # 浅色主题
            self.accent = "#5b6df0"
            self.accent_dark = "#4a59c9"
            self.accent_glow = "rgba(91, 109, 240, 0.16)"
            self.bg = "#f4f6fb"
            self.bg_top = "#fbfcff"
            self.bg_bottom = "#eef1f8"
            self.surface = "#ffffff"
            self.surface_2 = "#eef1f6"
            self.surface_3 = "#e2e7f0"
            self.border = "#d8dde8"
            self.border_light = "#c3cade"
            self.text = "#20232b"
            self.text_dim = "#7a8296"
            self.text_bright = "#11131a"
            self.scroll = "#c3cade"
            self.scroll_hover = "#a9b2cc"
        else:
            # 深色主题
            self.accent = "#7b8cff"
            self.accent_dark = "#5a66d6"
            self.accent_glow = "rgba(123, 140, 255, 0.15)"
            self.bg = "#0e0f13"
            self.bg_top = "#11131a"
            self.bg_bottom = "#0a0b0f"
            self.surface = "#16181e"
            self.surface_2 = "#1d2028"
            self.surface_3 = "#222631"
            self.border = "#272c36"
            self.border_light = "#343b4a"
            self.text = "#e7e9ee"
            self.text_dim = "#9aa1ad"
            self.text_bright = "#ffffff"
            self.scroll = "#2c3240"
            self.scroll_hover = "#3a4152"

        # 几何令牌
        self.radius = 10
        self.radius_sm = 7
        self.radius_md = 12

        # 派生渐变
        self.bg_gradient = (
            f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {self.bg_top}, stop:1 {self.bg_bottom})"
        )
        self.header_accent_line = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 transparent, stop:0.15 {self.accent}, "
            f"stop:0.5 {self.accent_glow}, stop:0.85 {self.accent}, stop:1 transparent)"
        )
        self.accent_btn_grad = (
            f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {self.accent}, stop:1 {self.accent_dark})"
        )


# 兼容现有引用：保留一份默认（深色）实例的导出快捷方式
_t = Theme()
ACCENT = _t.accent
ACCENT_DARK = _t.accent_dark
ACCENT_GLOW = _t.accent_glow
BG = _t.bg
BG_GRADIENT = _t.bg_gradient
SURFACE = _t.surface
SURFACE_2 = _t.surface_2
SURFACE_3 = _t.surface_3
BORDER = _t.border
BORDER_LIGHT = _t.border_light
TEXT = _t.text
TEXT_DIM = _t.text_dim
TEXT_BRIGHT = _t.text_bright


def build_style(theme: Theme | None = None) -> str:
    """根据主题令牌生成完整 QSS。"""
    if theme is None:
        theme = _t
    t = theme
    r, r_sm, r_md = t.radius, t.radius_sm, t.radius_md

    return f"""
/* ===== 全局 ===== */
QMainWindow, QDialog, QWizard, QMessageBox, QInputDialog {{
    background: {t.bg};
    color: {t.text};
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QWidget {{
    background: transparent;
    color: {t.text};
}}
QLabel {{ background: transparent; color: {t.text}; }}

/* ===== 顶栏 ===== */
QFrame#headerBar {{
    background: {t.bg_gradient};
    border-bottom: 2px solid {t.accent};
    border-bottom-color: {t.header_accent_line};
}}
QLabel#appName {{
    font-size: 18px;
    font-weight: bold;
    color: {t.text_bright};
    letter-spacing: 1px;
}}
QLabel#appTagline {{
    font-size: 11px;
    color: {t.text_dim};
    letter-spacing: 0.5px;
}}
QLabel#versionBadge {{
    font-size: 10px;
    font-weight: bold;
    color: {t.accent};
    background: {t.accent_glow};
    border: 1px solid {t.accent_dark};
    border-radius: {r}px;
    padding: 2px 10px;
}}

/* ===== 左侧导航栏 ===== */
QFrame#navRail {{
    background: {t.bg_gradient};
    border-right: 1px solid {t.border};
}}
QPushButton#navBtn {{
    min-height: 44px;
    min-width: 44px;
    max-width: 44px;
    background: transparent;
    color: {t.text_dim};
    border: 1px solid transparent;
    border-radius: {r_md}px;
    font-size: 15px;
}}
QPushButton#navBtn:checked {{
    background: {t.accent_glow};
    color: {t.accent};
    border: 1px solid {t.accent_dark};
}}
QPushButton#navBtn:hover:!checked {{
    background: {t.surface_3};
    color: {t.text};
    border-color: {t.border_light};
}}

/* ===== 侧边栏面板 ===== */
QFrame#sidePanel, QWidget#sidePanel {{
    background: {t.surface};
    border-right: 1px solid {t.border};
}}
QLabel#panelTitle {{
    font-size: 12px;
    font-weight: bold;
    color: {t.text_dim};
    letter-spacing: 1.5px;
    padding: 6px 4px;
    border-left: 3px solid {t.accent};
    padding-left: 8px;
}}

/* ===== 按钮 ===== */
QPushButton {{
    background: {t.surface_2};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: {r_sm}px;
    padding: 6px 14px;
    min-height: 20px;
}}
QPushButton:hover {{
    background: {t.surface_3};
    border-color: {t.border_light};
}}
QPushButton:pressed {{
    background: {t.accent_glow};
}}
QPushButton:focus {{
    border-color: {t.accent};
}}
QPushButton:default {{
    background: {t.accent_dark};
    border-color: {t.accent};
    color: white;
}}
QPushButton:disabled {{ color: {t.text_dim}; background: {t.surface}; }}
QPushButton#accentBtn {{
    background: {t.accent_btn_grad};
    color: white;
    border: none;
    border-radius: {r_sm}px;
    font-weight: bold;
    padding: 7px 16px;
}}
QPushButton#accentBtn:hover {{
    background: {t.accent};
}}
QPushButton#dangerBtn {{
    background: {"#e0483e" if not t.light else "#d64545"};
    color: white;
    border: none;
    border-radius: {r_sm}px;
    font-weight: bold;
    padding: 7px 16px;
}}
QPushButton#iconBtn {{
    background: transparent;
    border: none;
    padding: 4px;
    font-size: 16px;
}}
QPushButton#iconBtn:hover {{
    background: {t.surface_3};
    border-radius: {r_sm}px;
}}

/* ===== 输入框 ===== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: {r_sm}px;
    padding: 7px 10px;
    selection-background-color: {t.accent_dark};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {t.accent};
    background: {t.surface_2};
}}

QComboBox {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: {r_sm}px;
    padding: 5px 10px;
}}
QComboBox:hover {{ border-color: {t.border_light}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {t.surface_2};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: {r_sm}px;
    selection-background-color: {t.accent_dark};
}}
QComboBox::item {{ padding: 6px 8px; }}

QSpinBox, QDoubleSpinBox {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: {r_sm}px;
    padding: 4px 8px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {t.accent}; }}

/* ===== 列表 ===== */
QListWidget, QTableWidget {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: {r_sm}px;
    alternate-background-color: {t.surface_2};
}}
QListWidget::item {{ padding: 7px 10px; border-radius: {r_sm}px; border-bottom: 1px solid {t.surface_2}; }}
QListWidget::item:selected, QTableWidget::item:selected {{
    background: {t.accent_dark};
    color: white;
    border-left: 3px solid {t.accent};
}}
QListWidget::item:hover {{ background: {t.surface_3}; }}

QHeaderView::section {{
    background: {t.surface_2};
    color: {t.text_dim};
    border: none;
    border-bottom: 1px solid {t.border};
    padding: 6px 10px;
}}

/* ===== 标签页 ===== */
QTabWidget::pane {{
    border: 1px solid {t.border};
    border-radius: {r}px;
    background: {t.surface};
}}
QTabBar::tab {{
    background: transparent;
    color: {t.text_dim};
    padding: 9px 20px;
    border-bottom: 2px solid transparent;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    color: {t.text_bright};
    border-bottom: 2px solid {t.accent};
}}
QTabBar::tab:hover {{ color: {t.text}; }}

/* ===== 分割条 ===== */
QSplitter::handle {{
    background: {t.border};
    width: 1px;
    height: 1px;
}}
QSplitter::handle:hover {{ background: {t.accent}; }}

/* ===== 滚动条 ===== */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.scroll};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {t.scroll_hover}; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t.scroll};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {t.scroll_hover}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ===== 菜单栏 ===== */
QMenuBar {{
    background: {t.surface};
    color: {t.text};
    border-bottom: 1px solid {t.border};
    padding: 2px;
}}
QMenuBar::item {{ padding: 6px 10px; border-radius: {r_sm}px; }}
QMenuBar::item:selected {{
    background: {t.surface_3};
    border: 1px solid {t.border_light};
}}
QMenu {{
    background: {t.surface_2};
    color: {t.text};
    border: 1px solid {t.border_light};
    border-radius: {r_sm}px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 24px; border-radius: {r_sm}px; }}
QMenu::item:selected {{ background: {t.accent_dark}; }}
QMenu::separator {{ height: 1px; background: {t.border}; margin: 4px 8px; }}

/* ===== 提示 ===== */
QToolTip {{
    background: {t.surface_3};
    color: {t.text};
    border: 1px solid {t.border_light};
    border-radius: {r_sm}px;
    padding: 5px 9px;
}}

QGraphicsView {{
    background: {t.bg};
    border: 1px solid {t.border};
    border-radius: {r_sm}px;
}}

/* ===== 状态栏 ===== */
QStatusBar {{
    background: {t.surface};
    color: {t.text_dim};
    border-top: 1px solid {t.border};
    font-size: 11px;
}}
QStatusBar::item {{ border: none; }}
"""


STYLE = build_style()


def apply_theme(app, light: bool = False) -> None:
    """对应用实例应用主题。light=False 为深色，True 为浅色。"""
    app.setStyleSheet(build_style(Theme(light)))