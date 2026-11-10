# -*- coding: utf-8 -*-
"""配色 / 尺寸 / 字体 / 绘制工具。

配色：浅蓝渐变（用户参考图上蓝下近白）+ 角色原图的暖色点缀（腮红/爱心粉）。
"""
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainterPath, QPen


def qc(hexstr, alpha=255):
    c = QColor(hexstr)
    if alpha != 255:
        c.setAlpha(alpha)
    return c


# ---- 基础色（主题：浅蓝渐变，取自参考图上蓝下白） ----
INK = QColor("#12324B")          # 主文字：深湖蓝
INK_SOFT = QColor("#2A5675")
MUTED = QColor("#53799A")
NAVY = QColor("#2E5F8E")         # 强调蓝
NAVY_DEEP = QColor("#1B4467")
BLUSH = QColor("#F3BAB2")        # 角色腮红（暖色点缀）
PINK = QColor("#D98384")         # 爱心粉
KHAKI = QColor("#7E8FA0")

CREAM = QColor("#D7EAF7")        # 卡片中部
CREAM_TOP = QColor("#9DC1DD")    # 卡片顶部（参考图的蓝）
CREAM_BOTTOM = QColor("#F8FCFE") # 卡片底部接近白
ROW_BG = QColor("#FDFEFF")
ROW_BG_DONE = QColor("#E6F1FA")
TAB_BG = QColor("#A9CBE3")       # 标签轨（比卡片深一档）
SURFACE = QColor("#FFFFFF")
MENU_BG = QColor("#F6FBFE")

LINE = QColor("#16344F")
LINE.setAlpha(26)                # 极细描边
LINE_SOFT = QColor("#6E93AF")
LINE_SOFT.setAlpha(46)
STROKE = QColor("#6E93AF")
STROKE.setAlpha(96)              # 控件描边
STROKE_DOT = QColor("#8FA9BE")   # 空心圆/删除按钮的线

# ---- 尺寸 ----
CARD_W = 300
CARD_H = 318
CARD_RADIUS = 24
PAD = 16
ROW_H = 38
ROW_GAP = 7
INNER_W = CARD_W - PAD * 2          # 304

FONT_FAMILY = "Microsoft YaHei UI"
FONT_NUM = "Segoe UI Semibold"


def font(px, weight=QFont.Normal, family=None):
    f = QFont(family or FONT_FAMILY)
    f.setPixelSize(px)
    f.setWeight(weight)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def font_num(px, weight=QFont.DemiBold):
    f = QFont(FONT_NUM)
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


def card_gradient(rect):
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0.0, CREAM_TOP)
    g.setColorAt(0.55, CREAM)
    g.setColorAt(1.0, CREAM_BOTTOM)
    return g


def soft_shadow(painter, rect, radius, spread=11, alpha=8, offset=5, steps=6):
    """多层圆角矩形叠加出柔和投影；不依赖系统阴影，动画时实时跟随。"""
    painter.save()
    painter.setPen(Qt.NoPen)
    for i in range(steps, 0, -1):
        k = i / float(steps)
        r = rect.adjusted(-spread * k, -spread * k + offset, spread * k, spread * k + offset)
        col = QColor(30, 52, 73)
        col.setAlpha(max(2, int(alpha * (1.0 - k) + 2)))
        painter.setBrush(col)
        painter.drawRoundedRect(r, radius + spread * k, radius + spread * k)
    painter.restore()


def rounded_path(rect, radius):
    p = QPainterPath()
    p.addRoundedRect(rect, radius, radius)
    return p


def hairline(painter, rect, radius, color=LINE, width=1.0):
    pen = QPen(color)
    pen.setWidthF(width)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)


def draw_check(painter, rect, color=QColor(255, 255, 255), width=1.6):
    """手绘对勾（不使用系统图标）。"""
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    w = rect.width()
    h = rect.height()
    painter.drawLine(QPointF(rect.left() + w * 0.24, rect.top() + h * 0.54),
                     QPointF(rect.left() + w * 0.42, rect.top() + h * 0.71))
    painter.drawLine(QPointF(rect.left() + w * 0.42, rect.top() + h * 0.71),
                     QPointF(rect.left() + w * 0.79, rect.top() + h * 0.31))


def draw_cross(painter, rect, color, width=1.4):
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    k = min(rect.width(), rect.height()) * 0.27
    cx, cy = rect.center().x(), rect.center().y()
    painter.drawLine(QPointF(cx - k, cy - k), QPointF(cx + k, cy + k))
    painter.drawLine(QPointF(cx - k, cy + k), QPointF(cx + k, cy - k))
