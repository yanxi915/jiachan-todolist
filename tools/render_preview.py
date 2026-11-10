# -*- coding: utf-8 -*-
"""离屏渲染预览：把窗口画到图片上（模拟桌面背景），用于校验布局/透明/角色探出。

只用于开发自检，使用独立的临时数据目录，不会影响真实数据。
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

tmp = os.path.join(tempfile.gettempdir(), "peektodo_preview")
if os.path.isdir(tmp):
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(tmp, exist_ok=True)
os.environ["APPDATA"] = tmp
os.environ["PEEK_PREVIEW"] = "1"     # 强制写临时目录，绝不污染真实数据

from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication

from window import PeekWindow, WIN_W, WIN_H, COLL_W, COLL_H

app = QApplication(sys.argv)

win = PeekWindow(os.path.join(ROOT, "assets"))

# 造一些样例数据（仅作用于临时目录）
s = win.store
for t in ["把周报写完发给组里", "预约周五下午的牙科", "整理桌面文件"]:
    s.add_todo(t)
s.add_todo("买猫粮")
# 勾掉一条
first = s.todos()[0]["id"]
s.toggle_todo(first)
for h in ["喝水 8 杯", "睡前拉伸 10 分钟", "背 20 个单词"]:
    s.add_habit(h)
days = win._week_days()
hid = s.habits()[0]["id"]
for i in (0, 1, 2, 4):
    s.toggle_habit_day(hid, days[i][1])

win.show()
app.processEvents()


def shoot(name, tab=None, collapsed=False):
    if tab is not None:
        win.tabs.set_index(tab, animate=False)
        win._on_tab(tab)
    if collapsed:
        win._p = 1.0
        win.content.setVisible(False)
        win.resize(QSize(COLL_W, COLL_H))
    else:
        win._p = 0.0
        win.content.setVisible(True)
        win.resize(QSize(WIN_W, WIN_H))
    app.processEvents()
    shot = win.grab()

    # 模拟桌面背景（浅灰渐变 + 一个假窗口块），查看透明是否真的透出背景
    W, H = shot.width(), shot.height()
    canvas = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    canvas.fill(QColor(0, 0, 0, 0))
    p = QPainter(canvas)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, W, H)
    g.setColorAt(0, QColor("#8FA3B8"))
    g.setColorAt(1, QColor("#5D6E82"))
    p.fillRect(0, 0, W, H, g)
    p.setBrush(QColor(255, 255, 255, 40))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRect(10, 10, W - 60, H - 80), 8, 8)
    p.drawPixmap(0, 0, shot)
    p.end()
    out = os.path.join(ROOT, "assets", "_debug", name)
    canvas.save(out)
    print("saved", out, shot.size())


shoot("ui_todo.png", tab=0)
shoot("ui_habit.png", tab=2)
shoot("ui_collapsed.png", collapsed=True)

# 气泡（点左/右角色各一张，气泡在角色右侧）
for which, name in ((0, "ui_bubble_left.png"), (1, "ui_bubble_right.png")):
    win._p = 0.0
    win.content.setVisible(True)
    win.resize(QSize(WIN_W, WIN_H))
    win.on_char_click(which)
    win._bubble_anim.stop()
    win._bubble_alpha = 1.0
    win._bubble_timer.stop()
    app.processEvents()
    shoot(name)

