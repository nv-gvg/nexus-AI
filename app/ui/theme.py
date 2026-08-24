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
            self.text_green = "#1f9d61"
            self.danger = "#d64545"
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
            self.border = "#1c1f27"
            self.border_light = "#343b4a"
            self.text = "#e7e9ee"
            self.text_dim = "#9aa1ad"
            self.text_bright = "#ffffff"
            self.scroll = "#2c3240"
            self.scroll_hover = "#3a4152"
            self.text_green = "#7dd0a0"
            self.danger = "#ff6b6b"

        # 几何令牌
        # 圆角：更大更现代
        self.radius = 12
        self.radius_sm = 8
        self.radius_md = 14

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


# ------------------------------------------------------------------ 动态令牌
# 模块级快捷常量：随 apply_theme 切换主题同步更新，
# 保证运行期创建的控件（消息气泡、标签等）始终拿到当前主题颜色。
_current = Theme()


def current() -> Theme:
    """返回当前生效的主题实例（调用 apply_theme 后更新）。"""
    return _current


def _sync_aliases() -> None:
    global ACCENT, ACCENT_DARK, ACCENT_GLOW, BG, BG_GRADIENT
    global SURFACE, SURFACE_2, SURFACE_3, BORDER, BORDER_LIGHT
    global TEXT, TEXT_DIM, TEXT_BRIGHT, TEXT_GREEN, DANGER
    t = _current
    ACCENT = t.accent
    ACCENT_DARK = t.accent_dark
    ACCENT_GLOW = t.accent_glow
    BG = t.bg
    BG_GRADIENT = t.bg_gradient
    SURFACE = t.surface
    SURFACE_2 = t.surface_2
    SURFACE_3 = t.surface_3
    BORDER = t.border
    BORDER_LIGHT = t.border_light
    TEXT = t.text
    TEXT_DIM = t.text_dim
    TEXT_BRIGHT = t.text_bright
    TEXT_GREEN = t.text_green
    DANGER = t.danger


_sync_aliases()


def build_style(theme: Theme | None = None) -> str:
    """根据主题令牌生成完整 QSS。"""
    if theme is None:
        theme = _current
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
/* 独立弹窗面板（图谱/技能/工作流）统一底色，避免透明露出容器造成黑边 */
QWidget#panelRoot {{
    background: {t.bg};
}}
QLabel {{ background: transparent; color: {t.text}; }}

/* ===== 向导（QWizard）===== */
QWizard {{
    background: {t.bg};
    color: {t.text};
}}
QWizardPage {{
    background: {t.bg};
    color: {t.text};
}}
QWizard QLabel {{
    color: {t.text};
    background: transparent;
}}
QWizard QLabel[title="true"] {{
    color: {t.text_bright};
    font-size: 20px;
    font-weight: bold;
}}
QWizard > QFrame {{
    background: {t.bg};
    border: none;
}}
/* 向导底部按钮栏 */
QWizard QWidget#__qt__passivebuttonbox,
QWizard QDialogButtonBox {{
    background: {t.surface};
    border-top: 1px solid {t.border};
}}
/* 隐藏 ModernStyle 默认的深色标题栏背景 */
QWizard QWidget[wizardHeader="true"],
QWizard .QWizardHeader,
QWizard QBanner {{
    background: {t.bg};
    color: {t.text};
}}
/* 向导按钮 */
QWizard QPushButton {{
    min-width: 80px;
    min-height: 28px;
    padding: 6px 18px;
    background: {t.surface_2};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: {r_sm}px;
}}
QWizard QPushButton:hover {{ background: {t.surface_3}; }}
QWizard QPushButton:default {{
    background: {t.accent_btn_grad};
    color: white;
    border: none;
    font-weight: bold;
}}

/* ===== 顶栏 ===== */
QFrame#headerBar {{
    background: {t.bg};
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
    min-height: 48px;
    min-width: 48px;
    max-width: 48px;
    max-height: 48px;
    background: transparent;
    color: {t.text_dim};
    border: none;
    border-radius: {r}px;
    font-size: 18px;
    margin: 2px 4px;
}}
QPushButton#navBtn:checked {{
    background: {t.accent_glow};
    color: {t.accent};
    border: none;
}}
QPushButton#navBtn:hover:!checked {{
    background: {t.surface_3};
    color: {t.text};
    border: none;
}}

/* ===== 侧边栏面板 ===== */
QFrame#sidePanel, QWidget#sidePanel {{
    background: {t.bg};
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

/* ===== 分组框（设置页等）===== */
QGroupBox {{
    background: {t.surface_2};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: {r}px;
    margin-top: 10px;
    padding: 10px 12px 12px 12px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    color: {t.text_bright};
    font-size: 13px;
    background: {t.bg};
    border-radius: {r_sm}px;
}}
QGroupBox QLabel {{
    font-weight: normal;
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
    border: none;
    border-radius: {r_sm}px;
    alternate-background-color: {t.surface_2};
    gridline-color: {t.surface_2};
}}
QTableWidget::item {{ padding: 4px 8px; }}
QListWidget::item {{ padding: 7px 10px; border-radius: {r_sm}px; border-bottom: 1px solid {t.surface_2}; }}
QListWidget::item:selected, QTableWidget::item:selected {{
    background: {t.accent_dark};
    color: white;
    border-left: 3px solid {t.accent};
}}
QListWidget::item:hover {{ background: {t.surface_3}; }}
QTableWidget QTableCornerButton::section {{
    background: {t.surface_2};
    border: 1px solid {t.border};
}}
QScrollArea {{
    background: {t.surface};
    border: none;
}}

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

/* ===== 滚动条（窄条淡色，不抢视线）===== */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.scroll};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {t.scroll_hover}; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t.scroll};
    border-radius: 3px;
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
    global _current
    _current = Theme(light)
    _sync_aliases()
    app.setStyleSheet(build_style(_current))