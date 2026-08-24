"""莫比乌斯环：应用图标与主视觉渲染。

自适应系统配色 —— 系统深色时渲染白色环，系统浅色时渲染黑色环。
用参数方程 + 画家算法（深度排序 + 背面剔除）在纯 Python 中渲染。
"""

from __future__ import annotations

import math
import sys

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
    QRadialGradient,
    QPixmap,
)

# 强调色始终是冷蓝紫，在深/浅主题下都好看
ACCENT = "#7b8cff"


def _is_system_dark() -> bool:
    """检测当前界面是否为深色：优先使用应用已选主题，未设置时回退系统主题。"""
    try:
        from . import theme

        return not theme.current().light
    except Exception:
        pass
    # 回退：Windows 系统深色模式检测
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return val == 0
    except Exception:
        pass
    return True  # 默认深色


def _mobius(u: float, v: float) -> tuple[float, float, float]:
    """标准莫比乌斯带参数方程，u∈[0,2π]、v∈[-1,1]。"""
    half = u / 2.0
    c, s = math.cos(u), math.sin(u)
    ch, sh = math.cos(half), math.sin(half)
    r = 1.0 + (v / 2.0) * ch
    return (r * c, r * s, (v / 2.0) * sh)


def _rotate(p, rx, ry, rz):
    x, y, z = p
    c, s = math.cos(rx), math.sin(rx)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ry), math.sin(ry)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(rz), math.sin(rz)
    x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


def _normal(p0, p1, p2):
    ux, uy, uz = p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]
    vx, vy, vz = p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]
    return (uy*vz - uz*vy, uz*vx - ux*vz, ux*vy - uy*vx)


def _norm(v):
    n = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]) or 1.0
    return (v[0]/n, v[1]/n, v[2]/n)


def _base_palette(dark: bool) -> dict:
    """根据主题返回环面配色。"""
    if dark:
        # 深色背景 → 白色环
        return {
            "lo_r": 70, "lo_g": 75, "lo_b": 85,       # 暗部
            "hi_r": 250, "hi_g": 252, "hi_b": 255,    # 亮部
            "hi2_r": 255, "hi2_g": 220, "hi2_b": 240, # 高光
            "edge": QColor("#05060a"),
            "glow_alpha": 50,
        }
    # 浅色背景 → 黑色环
    return {
        "lo_r": 12, "lo_g": 14, "lo_b": 20,
        "hi_r": 60, "hi_g": 65, "hi_b": 80,
        "hi2_r": 100, "hi2_g": 80, "hi2_b": 120,
        "edge": QColor("#ffffff"),
        "glow_alpha": 18,
    }


def render_mobius(size: int = 480, dark: bool | None = None, accent: str = ACCENT) -> QPixmap:
    """渲染莫比乌斯带（透明背景，居中）。

    dark=None 时自动检测系统主题。
    """
    if dark is None:
        dark = _is_system_dark()
    pal = _base_palette(dark)

    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 背景柔光环
    glow = QRadialGradient(QPointF(size/2, size/2), size*0.48)
    c0 = QColor(accent)
    c0.setAlpha(pal["glow_alpha"])
    c1 = QColor(accent)
    c1.setAlpha(0)
    glow.setColorAt(0.0, c0)
    glow.setColorAt(0.6, QColor(accent).darker(200))
    glow.setColorAt(1.0, c1)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(glow))
    painter.drawEllipse(QRectF(0, 0, size, size))

    # 微星点装饰
    import random
    rng = random.Random(42)
    star_color = QColor(accent)
    star_color.setAlpha(50 if dark else 30)
    painter.setBrush(QBrush(star_color))
    for _ in range(12):
        sx = rng.uniform(size*0.1, size*0.9)
        sy = rng.uniform(size*0.1, size*0.9)
        sr = rng.uniform(0.5, 1.8)
        painter.drawEllipse(QPointF(sx, sy), sr, sr)

    U = 180
    SEG = 6
    rx, ry, rz = 1.05, -0.35, 0.0

    rows: list[list[tuple[float, float, float]]] = []
    for i in range(U + 1):
        u = 2.0 * math.pi * i / U
        row = [
            _rotate(_mobius(u, -1.0 + 2.0*j/(SEG-1)), rx, ry, rz)
            for j in range(SEG)
        ]
        rows.append(row)

    def project(p):
        x, y, z = p
        d = 4.2 + z
        scale = 3.4 / d
        return (size/2 + x*scale*size*0.34, size/2 - y*scale*size*0.34)

    light = _norm((0.40, 0.45, -0.80))
    ambient = 0.18

    quads: list[tuple[float, QPolygonF, QColor]] = []
    for i in range(U):
        for j in range(SEG - 1):
            a3 = rows[i][j]
            b3 = rows[i][j+1]
            c3 = rows[i+1][j+1]
            d3 = rows[i+1][j]

            pa = project(a3)
            pb = project(b3)
            pc = project(c3)
            pd = project(d3)

            cross = (pb[0]-pa[0])*(pd[1]-pa[1]) - (pb[1]-pa[1])*(pd[0]-pa[0])
            if cross <= 0:
                continue

            n = _normal(a3, b3, c3)
            if n[2] > 0:
                n = (-n[0], -n[1], -n[2])
            n = _norm(n)
            br = ambient + (1.0 - ambient) * max(0.0, n[0]*light[0] + n[1]*light[1] + n[2]*light[2])

            r = int(pal["lo_r"] + (pal["hi_r"]-pal["lo_r"])*br + (pal["hi2_r"]-pal["hi_r"])*br**4)
            g = int(pal["lo_g"] + (pal["hi_g"]-pal["lo_g"])*br + (pal["hi2_g"]-pal["hi_g"])*br**4)
            b = int(pal["lo_b"] + (pal["hi_b"]-pal["lo_b"])*br + (pal["hi2_b"]-pal["hi_b"])*br**4)
            color = QColor(min(r,255), min(g,255), min(b,255))

            depth = (a3[2]+b3[2]+c3[2]+d3[2]) / 4.0
            poly = QPolygonF([QPointF(*pa), QPointF(*pb), QPointF(*pc), QPointF(*pd)])
            quads.append((depth, poly, color))

    quads.sort(key=lambda q: q[0])
    painter.setPen(QPen(pal["edge"], 0.4))
    for _, poly, color in quads:
        painter.setBrush(QBrush(color))
        painter.drawPolygon(poly)

    painter.end()
    return pm


def make_logo(size: int = 64, dark: bool | None = None) -> QPixmap:
    """透明背景的小尺寸莫比乌斯环（用于顶栏/关于窗口）。"""
    return render_mobius(size, dark=dark)


def make_app_icon(size: int = 256) -> QIcon:
    """圆角底 + 莫比乌斯环的应用图标。底色自适应系统主题。"""
    dark = _is_system_dark()
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if dark:
        bg_top, bg_bot = "#161923", "#0a0b10"
        border = "#2c3242"
    else:
        bg_top, bg_bot = "#f5f6fa", "#e0e3eb"
        border = "#c8ccd6"

    bg = QLinearGradient(0, 0, size, size)
    bg.setColorAt(0.0, QColor(bg_top))
    bg.setColorAt(1.0, QColor(bg_bot))
    painter.setBrush(QBrush(bg))
    painter.setPen(QPen(QColor(border), 1.2))
    painter.drawRoundedRect(3, 3, size-6, size-6, size*0.22, size*0.22)
    painter.end()

    strip = render_mobius(int(size*0.76), dark=dark)
    painter = QPainter(pm)
    margin = (size - strip.width()) // 2
    painter.drawPixmap(margin, margin, strip)
    painter.end()

    return QIcon(pm)


def render_infinity_background(width: int, height: int, dark: bool | None = None) -> QPixmap:
    """生成半透明的无限符号背景装饰（用于主内容区背景）。"""
    if dark is None:
        dark = _is_system_dark()

    pm = QPixmap(width, height)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 无限符号颜色（根据主题）
    color = QColor(ACCENT)
    if dark:
        color.setAlpha(18)  # 深色主题下更透明
    else:
        color.setAlpha(10)  # 浅色主题下更透明

    pen = QPen(color, max(2, min(width, height) * 0.015))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    cx, cy = width / 2, height / 2
    size = min(width, height) * 0.35

    # 使用路径绘制无限符号
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()

    # 经典无限符号（双纽线）
    # 参数方程：x = 2cos(t)/(1+sin²(t)), y = 2sin(t)cos(t)/(1+sin²(t))
    import math
    steps = 200
    first = True
    for i in range(steps + 1):
        t = 2.0 * math.pi * i / steps
        sin_t = math.sin(t)
        cos_t = math.cos(t)
        denom = 1.0 + sin_t * sin_t
        x = (2.0 * cos_t / denom) * size * 0.5
        y = (2.0 * sin_t * cos_t / denom) * size * 0.5

        px = cx + x
        py = cy - y

        if first:
            path.moveTo(px, py)
            first = False
        else:
            path.lineTo(px, py)

    # 绘制主路径
    painter.drawPath(path)

    # 绘制外层光晕（更淡）
    glow_color = QColor(ACCENT)
    if dark:
        glow_color.setAlpha(8)
    else:
        glow_color.setAlpha(5)
    glow_pen = QPen(glow_color, max(8, min(width, height) * 0.05))
    glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(glow_pen)
    painter.drawPath(path)

    # 再绘制一次主线（确保清晰）
    painter.setPen(pen)
    painter.drawPath(path)

    painter.end()
    return pm
