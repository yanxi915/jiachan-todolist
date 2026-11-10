# -*- coding: utf-8 -*-
"""主窗口：无边框透明置顶卡片 + 角色探头 + 折叠收起 + 拖动吸附。"""
import ctypes
import datetime
import math
import os
import random
import time
from ctypes import wintypes

from PyQt5.QtCore import (QEasingCurve, QElapsedTimer, QEvent, QPoint, QPointF, QRect, QRectF, QSize,
                          Qt, QTimer, QVariantAnimation, pyqtSignal)
from PyQt5.QtGui import (QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QLinearGradient, QPainter,
                         QPainterPath, QPen, QRegion)
from PyQt5.QtWidgets import (QApplication, QGraphicsOpacityEffect, QLineEdit, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget)

import theme
from charview import CharacterPair
from store import Store
from theme import (BLUSH, CARD_H, CARD_RADIUS, CARD_W, CREAM, CREAM_BOTTOM, CREAM_TOP, INK,
                   INK_SOFT, INNER_W, LINE, LINE_SOFT, MENU_BG, MUTED, NAVY, NAVY_DEEP, PAD,
                   PINK, ROW_GAP, ROW_H, STROKE, STROKE_DOT, draw_check, font, font_num,
                   hairline, qc, soft_shadow)
from widgets import (AddButton, BubblePainter, HabitRow, IconButton, InlineInput, TabBar,
                     TaskRow)

WEEK_CN = "一二三四五六日"


def _dbg(text):
    """鼠标调试日志（仅 PEEK_DEBUG_MOUSE=1 时写 logs/mouse.log）。"""
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.makedirs(os.path.join(root, "logs"), exist_ok=True)
        with open(os.path.join(root, "logs", "mouse.log"), "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass

# 两位角色各自的台词（左侧卡其发偏淡定吐槽，右侧深蓝发偏活泼）
LINES = {
    "khaki": {
        0: ["又是待办…我先看一眼。", "慢慢来，别急。", "做不完也没关系。", "我坐这儿陪你。"],
        1: ["做完啦，厉害。", "嗯，不错。", "要不要喝口水？", "看你顺，心情也好。"],
        2: ["还没做完啊…", "时间有点紧哦。", "先把最急的做掉吧。", "别攒到最后呀。"],
    },
    "navy": {
        0: ["今天的待办，还剩几件？", "我在呢，随时喊我。", "一件一件来就好。", "做完记得勾掉哦。"],
        1: ["全部完成，太棒了！", "辛苦啦，抱一下～", "休息一下吧？", "看到勾勾就超开心。"],
        2: ["还剩几条呢…加油。", "有点急哦。", "先做最要紧的那件吧。", "要不要我提醒你？"],
    },
}

WIN_W, WIN_H = 450, 494
CARD = QRect(58, 170, CARD_W, CARD_H)       # 卡片 65..405 / 200..560
CHAR_POS = QPoint(72, 18)                   # 两位角色「整体」坐在卡片上沿（不拆开）
BUBBLE_Y = 12                               # 气泡在角色右侧
BUBBLE_MAX_W = 104

# 收起态：两位角色整体 + 一条进度小胶囊
COLL_W, COLL_H = 280, 198
COLL_CHAR = QPoint(8, 2)
COLL_CARD = QRect(10, 158, 260, 34)
COLL_PAD_T = 64        # 收起态窗口顶部多出来的透明区，专门留给气泡


def ui_safe(fn):
    """PyQt 里槽/虚函数抛异常会直接 abort 进程，这里统一兜住只记日志。"""
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception:
            import traceback
            try:
                _dbg("UI ERROR: " + traceback.format_exc())
            except Exception:
                pass
    return wrapper


class MiniMenu(QWidget):
    """自绘小菜单（右键用），常驻不闪：点菜单项 / 点外面 / 按 Esc 才关。"""

    ITEM_H = 34

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                         Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setWindowTitle("PeekTodo")
        self.items = []
        self._hover = -1
        self.setFixedSize(150, 12 + self.ITEM_H * 3)
        # 单实例复用：事件过滤器只装一次，窗口对象不会被销毁，避免野指针崩溃
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def set_items(self, items):
        self.items = items
        self._hover = -1
        self.setFixedSize(150, 12 + self.ITEM_H * len(items))
        self.update()

    def show_at(self, global_pos):
        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        size = self.size()
        x = max(area.left() + 4, min(global_pos.x() + 2, area.right() - size.width() - 4))
        y = max(area.top() + 4, min(global_pos.y() + 2, area.bottom() - size.height() - 4))
        self.move(x, y)
        self.show()
        self.raise_()

    def eventFilter(self, obj, ev):
        """点菜单外面任意位置就关；菜单内部点击不关。"""
        try:
            return self._handle_event(obj, ev)
        except Exception:
            return False

    def _handle_event(self, obj, ev):
        if not self.isVisible():
            return False
        t = ev.type()
        if t == QEvent.MouseButtonPress:
            try:
                gp = ev.globalPos()
            except Exception:
                gp = None
            if gp is None or not self.geometry().contains(gp):
                self.hide()
        elif t == QEvent.KeyPress and ev.key() == Qt.Key_Escape:
            self.hide()
            return True
        return False

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(qc("#16344F", 40))
        p.drawRoundedRect(r.adjusted(0, 2, 0, 0), 12, 12)
        p.setBrush(MENU_BG)
        p.drawRoundedRect(r, 12, 12)
        p.setPen(QPen(qc("#6E93AF", 70), 1))
        p.drawRoundedRect(r, 12, 12)
        p.setFont(font(12))
        for i, (label, _cb) in enumerate(self.items):
            ir = QRectF(6, 6 + i * self.ITEM_H, r.width() - 12, self.ITEM_H - 4)
            if i == self._hover:
                p.setPen(Qt.NoPen)
                p.setBrush(qc("#2E5F8E", 26))
                p.drawRoundedRect(ir, 9, 9)
            p.setPen(INK if i == self._hover else INK_SOFT)
            p.drawText(ir.adjusted(10, 0, -10, 0), Qt.AlignVCenter | Qt.AlignLeft, label)

    @ui_safe
    def mouseMoveEvent(self, e):
        idx = int((e.pos().y() - 6) // self.ITEM_H)
        idx = idx if 0 <= idx < len(self.items) else -1
        if idx != self._hover:
            self._hover = idx
            self.update()

    @ui_safe
    def mouseReleaseEvent(self, e):
        idx = int((e.pos().y() - 6) // self.ITEM_H)
        cb = None
        if 0 <= idx < len(self.items):
            cb = self.items[idx][1]
        self.hide()
        if cb is not None:
            cb()


class PeekWindow(QWidget):
    def __init__(self, assets_dir):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool |
                            Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setWindowTitle("探头待办")
        self.resize(WIN_W, WIN_H)

        self.store = Store(self)
        self.char = CharacterPair(assets_dir, phase=0.0)
        self.chars = [self.char]

        self._p = 0.0                  # 0=展开 1=收起
        self._collapsed = False
        self._expanded_pos = QPoint(700, 120)
        self._press_pos = None
        self._press_win = None
        self._moved = False
        self._drag_ok = False
        self._collapsing = False
        self._menu = MiniMenu(self)
        # 悬停自动收起/展开
        self._hover_out_since = None
        self._hover_in_since = None
        self._need_leave = False
        self._hover_armed = True      # 展开后光标真的进来过一次，才允许自动收起
        self._hover_grace = time.monotonic() + 4.0
        self._tab = int(self.store.ui().get("tab") or 0)
        self._bubble_timer = QTimer(self)
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.timeout.connect(self._fade_bubble)

        self._build_ui()
        self._build_timers()
        self._restore_position()
        self._rebuild_list()
        self._update_header_cache()
        if os.environ.get("PEEKTODO_DEMO") == "1":
            QTimer.singleShot(700, self._demo_bubble)

    def _demo_bubble(self):
        self.on_char_click()
        self._bubble_timer.stop()

    # ================= UI 组装 =================
    def _build_ui(self):
        self.content = QWidget(self)
        self.content.setGeometry(CARD)
        self.content.setAttribute(Qt.WA_TranslucentBackground, True)
        self._opacity = QGraphicsOpacityEffect(self.content)
        self._opacity.setOpacity(1.0)
        self.content.setGraphicsEffect(self._opacity)

        self.btn_min = IconButton("min", 20, self.content)
        self.btn_min.move(PAD, 13)
        self.btn_min.setToolTip("收起为角色探头")
        self.btn_min.clicked.connect(self.collapse)

        self.btn_close = IconButton("close", 20, self.content, tone="danger")
        self.btn_close.move(PAD + 26, 13)
        self.btn_close.setToolTip("退出")
        self.btn_close.clicked.connect(self.quit_app)

        self.tabs = TabBar(self.content)
        self.tabs.setGeometry(PAD, 84, INNER_W, 30)
        self.tabs.set_index(self._tab, animate=False)
        self.tabs.currentChanged.connect(self._on_tab)

        self.list = QScrollArea(self.content)
        self.list.setGeometry(PAD, 116, INNER_W, 146)
        self.list.setFrameShape(QScrollArea.NoFrame)
        self.list.setWidgetResizable(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}"
            "QScrollBar:vertical{background:transparent;width:6px;margin:0;}"
            "QScrollBar::handle:vertical{background:rgba(42,55,82,60);border-radius:3px;min-height:26px;}"
            "QScrollBar::handle:vertical:hover{background:rgba(42,55,82,95);}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;background:transparent;}"
            "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}"
        )
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.host = QWidget(self.list)
        self.host.setAttribute(Qt.WA_TranslucentBackground, True)
        self.host_layout = QVBoxLayout(self.host)
        self.host_layout.setContentsMargins(0, 0, 6, 0)
        self.host_layout.setSpacing(ROW_GAP)
        self.host_layout.setAlignment(Qt.AlignTop)
        self.list.setWidget(self.host)

        self.add_btn = AddButton("新增待办", self.content)
        self.add_btn.setGeometry(PAD, 266, INNER_W, 30)
        self.add_btn.clicked.connect(self._on_add_clicked)

        self._input = None
        self._input_kind = None

        # 台词气泡（直接画在窗口透明层上，避免子控件在分层窗口里不刷新）
        self._bubble_text = ""
        self._bubble_rect = QRect(164, 12, 120, 44)
        self._bubble_alpha = 0.0

    def _build_timers(self):
        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_t = 0.0
        self.anim = QTimer(self)
        self.anim.setInterval(33)
        self.anim.timeout.connect(self._on_tick)
        self.anim.start()

        self.sec_timer = QTimer(self)
        self.sec_timer.setInterval(1000)
        self.sec_timer.timeout.connect(self._on_second)
        self.sec_timer.start()

        self.guard_timer = QTimer(self)
        self.guard_timer.setInterval(2000)
        self.guard_timer.timeout.connect(self._guard_onscreen)
        self.guard_timer.start()

        self.hover_timer = QTimer(self)
        self.hover_timer.setInterval(150)
        self.hover_timer.timeout.connect(self._on_hover_tick)
        self.hover_timer.start()

        self.talk_timer = QTimer(self)
        self.talk_timer.setInterval(5000)     # 每 5 秒换一次表情 + 冒一句话
        self.talk_timer.timeout.connect(self._auto_talk)
        self.talk_timer.start()

        self.collapse_anim = QVariantAnimation(self)
        self.collapse_anim.setDuration(340)
        self.collapse_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.collapse_anim.valueChanged.connect(self._on_collapse_value)
        self.collapse_anim.finished.connect(self._on_collapse_finished)

        self._bubble_anim = QVariantAnimation(self)
        self._bubble_anim.setDuration(240)
        self._bubble_anim.valueChanged.connect(self._on_bubble_value)

    # ================= 几何 / 绘制 =================
    def _lerp_rect(self, a, b):
        p = self._p
        return QRect(int(a.x() + (b.x() - a.x()) * p), int(a.y() + (b.y() - a.y()) * p),
                     int(a.width() + (b.width() - a.width()) * p),
                     int(a.height() + (b.height() - a.height()) * p))

    def _card_rect(self):
        r = self._lerp_rect(CARD, COLL_CARD)
        pad = int(round(COLL_PAD_T * self._p))
        return r.translated(0, pad)

    def _char_pos(self, i=0):
        p = self._p
        pad = COLL_PAD_T * p
        return QPointF(CHAR_POS.x() + (COLL_CHAR.x() - CHAR_POS.x()) * p,
                       CHAR_POS.y() + (COLL_CHAR.y() - CHAR_POS.y()) * p + pad)

    def _char_region(self, i=0):
        spr = self.chars[0]
        off = spr.float_offset()
        pos = self._char_pos(0)
        return QRect(int(pos.x()) - 4, int(pos.y() + off) - 4,
                     spr.size[0] + 8, spr.size[1] + 8)

    def _all_char_region(self):
        return self._char_region(0)

    def paintEvent(self, e):
        try:
            self._paint_all()
        except Exception:
            import traceback
            try:
                _dbg('PAINT CRASH: ' + traceback.format_exc())
            except Exception:
                pass

    def _paint_all(self):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.LosslessImageRendering)

        card = self._card_rect()
        radius = CARD_RADIUS + (20 - CARD_RADIUS) * self._p
        soft_shadow(p, QRectF(card), radius)

        # 两位角色（原图并排、不拆开）坐在卡片上沿，卡片压住脚底 4px
        spr = self.chars[0]
        spr.paint(p, self._char_pos(0), spr.float_offset())

        grad = QLinearGradient(card.topLeft(), card.bottomLeft())
        grad.setColorAt(0.0, theme.CREAM_TOP)
        grad.setColorAt(0.55, theme.CREAM)
        grad.setColorAt(1.0, theme.CREAM_BOTTOM)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(card), radius, radius)
        hairline(p, QRectF(card), radius, LINE_SOFT, 1.0)

        if self._p < 0.25:
            p.setOpacity(1.0 - self._p / 0.25)
            self._paint_header(p, card, radius)
            p.setOpacity(1.0)
        if self._p > 0.5:
            p.setOpacity(min(1.0, (self._p - 0.5) / 0.5))
            self._paint_tab_decoration(p, card, radius)
            p.setOpacity(1.0)

        # 台词气泡（在卡片与角色之上，位于窗口顶部透明区）
        if self._bubble_alpha > 0.02 and self._bubble_text:
            p.setOpacity(min(1.0, self._bubble_alpha))
            BubblePainter.draw(p, self._bubble_box(), self._bubble_text, self._bubble_tip())
            p.setOpacity(1.0)

    def _paint_header(self, p, card, radius):
        """时间 / 日期 / 进度（全部限制在卡片内部）。"""
        x0 = card.x() + PAD
        right = card.right() - PAD
        top = card.y()

        # 24h 时间
        f = font_num(24)
        p.setFont(f)
        p.setPen(INK)
        fm = QFontMetrics(f)
        tw = fm.horizontalAdvance(self._time_str)
        p.drawText(QRectF(right - tw - 2, top + 4, tw + 4, 32), Qt.AlignVCenter | Qt.AlignRight,
                   self._time_str)

        # 日期 + 星期
        f2 = font(10)
        p.setFont(f2)
        p.setPen(MUTED)
        fm2 = QFontMetrics(f2)
        dw = fm2.horizontalAdvance(self._date_str)
        p.drawText(QRectF(right - dw - 1, top + 36, dw + 2, 15),
                   Qt.AlignVCenter | Qt.AlignRight, self._date_str)

        # 进度标题
        f3 = font(10, QFont.DemiBold)
        p.setFont(f3)
        p.setPen(INK_SOFT)
        p.drawText(QRectF(x0, top + 50, 110, 16), Qt.AlignVCenter | Qt.AlignLeft, "今日进度")

        done, total = self.store.progress()
        p.setFont(font(10, QFont.DemiBold))
        p.setPen(NAVY)
        ratio = (done / float(total)) if total else 0.0
        label = "%d / %d" % (done, total)
        if total:
            label += "   %d%%" % int(round(ratio * 100))
        fm3 = QFontMetrics(font(10, QFont.DemiBold))
        lw = fm3.horizontalAdvance(label)
        p.drawText(QRectF(right - lw, top + 50, lw + 2, 16), Qt.AlignVCenter | Qt.AlignRight, label)

        # 细进度条
        bar = QRectF(x0, top + 70, card.width() - PAD * 2, 4)
        p.setPen(Qt.NoPen)
        p.setBrush(qc("#FFFFFF", 128))
        p.drawRoundedRect(bar, 2.5, 2.5)
        if ratio > 0:
            fill = QRectF(bar.x(), bar.y(), max(6.0, bar.width() * ratio), bar.height())
            g = QLinearGradient(fill.topLeft(), fill.topRight())
            g.setColorAt(0.0, NAVY)
            g.setColorAt(1.0, BLUSH)
            p.setBrush(g)
            p.drawRoundedRect(fill, 2.5, 2.5)

        # 空列表提示
        if self._rows_count == 0 and self._input is None and self._p < 0.5:
            p.setFont(font(11, QFont.Normal))
            p.setPen(qc("#7C97AD"))
            tips = {0: "还没有待办，点下方「新增待办」", 1: "完成的待办会出现在这里",
                    2: "还没有打卡习惯，点下方新增一条"}
            p.drawText(QRectF(card.x() + PAD, card.y() + 172, card.width() - PAD * 2, 60),
                       Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, tips.get(self._tab, ""))

    def _paint_tab_decoration(self, p, card, radius):
        """收起态小胶囊：今日进度 + 细进度条。"""
        done, total = self.store.progress()
        ratio = (done / float(total)) if total else 0.0

        p.setPen(INK_SOFT)
        p.setFont(font(10, QFont.DemiBold))
        p.drawText(QRectF(card.x(), card.y() + 4, card.width(), 15),
                   Qt.AlignHCenter | Qt.AlignVCenter, "今日 %d / %d 待办" % (done, total))

        bar = QRectF(card.x() + 22, card.bottom() - 11, card.width() - 44, 3.5)
        p.setPen(Qt.NoPen)
        p.setBrush(qc("#FFFFFF", 120))
        p.drawRoundedRect(bar, 2, 2)
        if ratio > 0:
            p.setBrush(NAVY)
            p.drawRoundedRect(QRectF(bar.x(), bar.y(), max(4.0, bar.width() * ratio), bar.height()), 2, 2)

    # ================= 动画 =================
    def _on_tick(self):
        now = self._clock.elapsed() / 1000.0
        dt = min(0.06, now - self._last_t)
        self._last_t = now
        if dt <= 0:
            return
        # 收起/展开动画进行中把漂浮冻住，避免两种位移叠加看着像抖
        need = self.char.tick(0.0 if self._collapsing else dt)
        if need and not self._collapsing:
            self.update(self._all_char_region())

    def _on_second(self):
        changed = False
        now_t, now_d = self._now_time(), self._now_date()
        if now_t != self._time_str:
            self._time_str = now_t
            changed = True
        if now_d != self._date_str:
            self._date_str = now_d
            changed = True
            if self._tab == 2:
                self._rebuild_list()
        if changed:
            self.update(self._header_rect())

    def _header_rect(self):
        card = self._card_rect()
        return QRect(card.x(), card.y(), card.width(), 92)

    def _now_time(self):
        return datetime.datetime.now().strftime("%H:%M")

    def _now_date(self):
        d = datetime.datetime.now()
        return "%d月%d日 周%s" % (d.month, d.day, WEEK_CN[d.weekday()])

    def _update_header_cache(self):
        self._time_str = self._now_time()
        self._date_str = self._now_date()

    # ================= 列表 =================
    def _clear_layout(self):
        while self.host_layout.count():
            item = self.host_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _rebuild_list(self):
        self._clear_layout()
        self._input = None
        self._input_kind = None
        self._rows_count = 0

        if self._tab == 2:
            days = self._week_days()
            for h in self.store.habits():
                row = HabitRow(h, days, self.host)
                row.day_toggled.connect(self._on_habit_toggle)
                row.deleted.connect(self._on_habit_delete)
                row.renamed.connect(self._on_habit_rename)
                self.host_layout.addWidget(row)
                self._rows_count += 1
        else:
            want_done = (self._tab == 1)
            for t in self.store.todos():
                if bool(t.get("done")) != want_done:
                    continue
                row = TaskRow(t, self.host)
                row.toggled.connect(self._on_todo_toggle)
                row.deleted.connect(self._on_todo_delete)
                row.renamed.connect(self._on_todo_rename)
                self.host_layout.addWidget(row)
                self._rows_count += 1
        self.host_layout.addStretch(1)
        # 没有内容时彻底隐藏滚动条（否则空列表右侧会挂一条灰条）
        if self._rows_count == 0:
            self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.add_btn.set_text("新增打卡" if self._tab == 2 else "新增待办")
        self.add_btn.setVisible(self._tab != 1)
        QTimer.singleShot(0, self._sync_host_height)
        self.update(self._header_rect())

    def _sync_host_height(self):
        items = []
        for i in range(self.host_layout.count()):
            w = self.host_layout.itemAt(i).widget()
            if w is not None:
                items.append(w)
        extra = sum(w.height() for w in items) + ROW_GAP * max(0, len(items) - 1) + 8
        self.host.setMinimumHeight(max(extra, 152))

    def _week_days(self):
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        out = []
        for i in range(7):
            d = monday + datetime.timedelta(days=i)
            out.append((WEEK_CN[i], d.strftime("%Y-%m-%d"), d == today))
        return out

    # ---- 待办操作 ----
    def _on_todo_toggle(self, tid):
        self.store.toggle_todo(tid)
        self._rebuild_list()
        self._flash_character(1 if self.store.progress()[0] else 0)

    def _on_todo_delete(self, tid):
        self.store.delete_todo(tid)
        self._rebuild_list()

    def _on_todo_rename(self, tid, text):
        self.store.update_todo(tid, text)

    # ---- 打卡操作 ----
    def _on_habit_toggle(self, hid, key):
        self.store.toggle_habit_day(hid, key)
        for i in range(self.host_layout.count()):
            w = self.host_layout.itemAt(i).widget()
            if isinstance(w, HabitRow) and w.hid == hid:
                for h in self.store.habits():
                    if h["id"] == hid:
                        w.checks = dict(h.get("checks") or {})
                        break
                w.update()
                break

    def _on_habit_delete(self, hid):
        self.store.delete_habit(hid)
        self._rebuild_list()

    def _on_habit_rename(self, hid, text):
        self.store.rename_habit(hid, text)

    def _on_tab(self, idx):
        self._tab = idx
        self.store.set_ui(tab=idx)
        self._rebuild_list()
        self.update()

    # ---- 新增 ----
    def _on_add_clicked(self):
        self._open_input()

    def _open_input(self, focus=True):
        kind = "habit" if self._tab == 2 else "todo"
        if self._input is not None and self._input_kind == kind:
            self._input.focus()
            return
        self._remove_input(rebuild=False)
        ph = "添加打卡习惯，回车确认" if kind == "habit" else "添加待办，回车确认"
        inp = InlineInput(ph, 36, self.host)
        inp.submitted.connect(self._on_input_submit)
        inp.cancelled.connect(lambda: self._remove_input())
        self.host_layout.insertWidget(0, inp)
        self._input = inp
        self._input_kind = kind
        self._sync_host_height()
        self.list.verticalScrollBar().setValue(0)
        if focus:
            QTimer.singleShot(20, inp.focus)

    def _remove_input(self, rebuild=True):
        if self._input is None:
            return
        w = self._input
        self._input = None
        self._input_kind = None
        self.host_layout.removeWidget(w)
        w.setParent(None)
        w.deleteLater()
        self._sync_host_height()
        if rebuild:
            self.update(self._header_rect())

    def _on_input_submit(self, text):
        if not text.strip():
            return
        if self._input_kind == "habit":
            self.store.add_habit(text)
        else:
            self.store.add_todo(text)
        self._rebuild_list()
        self._open_input(focus=True)
        self._flash_character(0)

    # ================= 角色交互 =================
    def _flash_character(self, expr):
        """勾选完成时两位角色一起换成笑脸（原图整体贴图），短暂保持。"""
        spr = self.char
        if expr == 1 and spr.index != 1:
            spr.set_index(1)
            QTimer.singleShot(1800, self._restore_char_face)
            self.update(self._all_char_region())

    def _restore_char_face(self):
        self.char.set_index(0)
        self.update(self._all_char_region())

    def on_char_click(self, which=0):
        spr = self.char
        idx = spr.next_expression()
        key = "khaki" if which == 0 else "navy"
        self._say(random.choice(LINES[key].get(idx, LINES[key][0])), which)
        self.update(self._all_char_region())

    def _bubble_box(self):
        """气泡矩形：展开态贴角色右侧，收起态落在探头上方那条透明区。"""
        w = getattr(self, "_bubble_w", 0) or 110
        h = getattr(self, "_bubble_h", 0) or 44
        p = self._p
        x_open = WIN_W - 8 - w
        x_coll = COLL_W - 8 - w
        y_open = BUBBLE_Y
        y_coll = 4 - COLL_PAD_T          # 内容坐标系里的 y（绘制时再加回留白）
        x = x_open + (x_coll - x_open) * p
        y = y_open + (y_coll - y_open) * p + COLL_PAD_T * p
        return QRect(int(round(x)), int(round(y)), w, h)

    def _bubble_tip(self):
        spr = self.char
        pos = self._char_pos(0)
        which = getattr(self, "_bubble_which", 0)
        return int(pos.x() + spr.size[0] * (0.215 if which == 0 else 0.715))

    def _say(self, text, which=0):
        """台词放在角色旁不压住角色；收起态自动挪到探头上方。"""
        size = BubblePainter.measure(text, BUBBLE_MAX_W)
        self._bubble_w = size.width()
        self._bubble_h = size.height()
        self._bubble_which = which
        self._bubble_text = text
        self._bubble_rect = self._bubble_box()
        self._bubble_anim.stop()
        self._bubble_anim.setStartValue(self._bubble_alpha)
        self._bubble_anim.setEndValue(1.0)
        self._bubble_anim.start()
        self.update()
        self._bubble_timer.start(3600)

    def _on_bubble_value(self, v):
        self._bubble_alpha = float(v)
        self.update()

    def _fade_bubble(self):
        self._bubble_anim.stop()
        self._bubble_anim.setStartValue(self._bubble_alpha)
        self._bubble_anim.setEndValue(0.0)
        self._bubble_anim.start()
        QTimer.singleShot(300, self._clear_bubble)

    def _clear_bubble(self):
        if self._bubble_alpha <= 0.02:
            self._bubble_text = ""
            self.update()

    # ================= 折叠 =================
    def collapse(self):
        if self._collapsed:
            return
        self._close_menu()
        self._expanded_pos = self.pos()
        self._need_leave = True       # 收起后要先把鼠标移开，才不会立刻弹回去
        self._hover_armed = False
        self._hover_out_since = None
        self.store.set_ui(x=self.pos().x(), y=self.pos().y())
        self._bubble_text = ""
        self._bubble_alpha = 0.0
        target = self._collapse_geometry()
        self._start_collapse(0.0, 1.0, self.geometry(), target)
        self._collapsed = True

    def expand(self):
        if not self._collapsed:
            return
        target = QRect(self._expanded_pos, QSize(WIN_W, WIN_H))
        target = self._clamp_to_screen(target)
        # _on_collapse_value 里 rect = a + (b-a)*v：v=0 对应 a，v=1 对应 b。
        # 展开时 v 从 1 走到 0，所以 a 必须是「展开后的几何」，b 才是当前收起几何。
        self._start_collapse(1.0, 0.0, target, self.geometry())
        self._hover_grace = time.monotonic() + 1.2
        self._hover_armed = False
        self._collapsed = False

    def _start_collapse(self, a, b, geo_a, geo_b):
        self._geo_a = geo_a
        self._geo_b = geo_b
        self._collapsing = True
        self.collapse_anim.stop()
        self.collapse_anim.setStartValue(a)
        self.collapse_anim.setEndValue(b)
        self.collapse_anim.start()

    def _on_collapse_finished(self):
        self._collapsing = False
        self._save_position()

    def _on_collapse_value(self, v):
        v = float(v)
        self._p = v
        ga, gb = self._geo_a, self._geo_b
        rect = QRect(int(ga.x() + (gb.x() - ga.x()) * v), int(ga.y() + (gb.y() - ga.y()) * v),
                     int(ga.width() + (gb.width() - ga.width()) * v),
                     int(ga.height() + (gb.height() - ga.height()) * v))
        self.setGeometry(rect)
        self.content.setGeometry(self._card_rect())
        fade = max(0.0, min(1.0, (0.25 - v) / 0.25))    # v 越小越不透明
        self._opacity.setOpacity(fade)
        self.content.setVisible(v < 0.25)
        self.update()

    def _collapse_geometry(self):
        screen = self._screen_rect()
        geo = self.geometry()
        dx = CHAR_POS.x() - COLL_CHAR.x()
        dy = CHAR_POS.y() - COLL_CHAR.y()
        rect = QRect(geo.x() + dx, geo.y() + dy, COLL_W, COLL_H)
        card = QRect(geo.x() + CARD.x(), geo.y() + CARD.y(), CARD.width(), CARD.height())
        edges = [("left", card.left() - screen.left()),
                 ("right", screen.right() - card.right()),
                 ("top", card.top() - screen.top()),
                 ("bottom", screen.bottom() - card.bottom())]
        near, dist = min(edges, key=lambda kv: kv[1])
        if dist < 44:
            if near == "left":
                rect.moveLeft(screen.left())
            elif near == "right":
                rect.moveRight(screen.right())
            elif near == "top":
                rect.moveTop(screen.top() - 4)
            elif near == "bottom":
                rect.moveBottom(screen.bottom() + 4)
        # 顶部留白只加在窗口上，可见内容（角色+胶囊）位置不变
        rect = QRect(rect.x(), rect.y() - COLL_PAD_T, COLL_W, COLL_H + COLL_PAD_T)
        return self._clamp_to_screen(rect, allow_top=COLL_PAD_T)

    def _screen_rect(self):
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _clamp_to_screen(self, rect, allow_top=0):
        """把整个窗口留在屏幕内（拖拽过程中不限制，用户仍可拖到边缘触发收起）。"""
        s = self._screen_rect()
        x = max(s.left(), min(rect.x(), s.right() - rect.width() + 1))
        y = max(s.top() - allow_top,
                min(rect.y(), s.bottom() - rect.height() + 1))
        return QRect(x, y, rect.width(), rect.height())

    # ================= 位置 =================
    def _restore_position(self):
        ui = self.store.ui()
        x, y = ui.get("x"), ui.get("y")
        if isinstance(x, int) and isinstance(y, int):
            rect = self._clamp_to_screen(QRect(x, y, WIN_W, WIN_H))
            self.move(rect.topLeft())
            self._expanded_pos = rect.topLeft()
        else:
            s = QGuiApplication.primaryScreen().availableGeometry()
            self.move(s.right() - WIN_W - 24, s.top() + 80)
            self._expanded_pos = self.pos()
        self.setGeometry(QRect(self.pos(), QSize(WIN_W, WIN_H)))

    def _save_position(self):
        rect = self._clamp_to_screen(QRect(self.pos(), self.size()),
                                     allow_top=COLL_PAD_T if self._collapsed else 0)
        if rect.topLeft() != self.pos():
            self.move(rect.topLeft())
        if self._collapsed:
            return
        self.store.set_ui(x=self.pos().x(), y=self.pos().y())

    def _guard_onscreen(self):
        """兜底：任何时候都不让窗口停在屏幕外（拖动中不打扰）。"""
        if not (QApplication.mouseButtons() & Qt.LeftButton):
            self._press_pos = None          # 松手事件丢了也要能恢复
        if self._press_pos is not None or self._collapsing:
            return
        rect = self._clamp_to_screen(QRect(self.pos(), self.size()),
                                     allow_top=COLL_PAD_T if self._collapsed else 0)
        if rect.topLeft() != self.pos():
            self.move(rect.topLeft())
            if not self._collapsed:
                self.store.set_ui(x=rect.x(), y=rect.y())

    # ================= 悬停自动收起 / 展开 =================
    def _on_hover_tick(self):
        try:
            self._hover_step()
        except Exception:
            pass

    def _hover_inside(self, pos):
        """鼠标是否落在「看得见的面板」上（卡片/角色/气泡），透明边距不算。"""
        if self._collapsed:
            vis = QRect(0, COLL_PAD_T, COLL_W, COLL_H)    # 角色 + 胶囊，不含顶部透明区
            if vis.contains(pos):
                return True
            if self._bubble_alpha > 0.05 and self._bubble_text:
                if self._bubble_box().adjusted(-6, -6, 6, 6).contains(pos):
                    return True
            return False
        if self._card_rect().adjusted(-12, -12, 12, 12).contains(pos):
            return True
        if self._bubble_alpha > 0.05 and self._bubble_text:
            if self._bubble_rect.adjusted(-8, -8, 8, 8).contains(pos):
                return True
        return self._in_char(pos)

    def _hover_step(self):
        if self._collapsing or self._press_pos is not None or self._drag_ok:
            return
        try:
            if self._menu is not None and self._menu.isVisible():
                return
        except RuntimeError:
            return
        local = self.mapFromGlobal(QCursor.pos())
        inside = self._hover_inside(local)
        now = time.monotonic()

        if self._collapsed:
            if not inside:
                self._need_leave = False       # 鼠标真的离开过探头，才允许再次展开
                self._hover_in_since = None
                return
            if self._need_leave:
                return
            if self._hover_in_since is None:
                self._hover_in_since = now
            elif now - self._hover_in_since >= 0.25:
                self._hover_in_since = None
                self.expand()
            return

        # 展开态：光标真正进来过之后，停在外面 0.65s 才收成探头
        if inside:
            self._hover_armed = True
            self._hover_out_since = None
            return
        if not self._hover_armed:
            return
        if now < self._hover_grace:
            return
        if self._hover_out_since is None:
            self._hover_out_since = now
        elif now - self._hover_out_since >= 0.65:
            self._hover_out_since = None
            self.collapse()

    def _auto_talk(self):
        """每 5 秒：换一个表情 + 冒一句对得上的台词。"""
        try:
            if self._collapsing:
                return
            if self._collapsed:
                if self._p < 0.95:        # 还没收干净，等一等
                    return
            elif self._p > 0.05:
                return
            if self._input is not None:
                return
            if self.hover_timer.isActive() and self._press_pos is not None:
                return
            which = 0 if random.random() < 0.5 else 1
            self.on_char_click(which)
        except Exception:
            pass

    # ================= 鼠标 =================
    def _which_char(self, pos):
        """整张并排贴图里，点左半边算左角色(0)，右半边算右角色(1)，没碰到 -1。"""
        spr = self.char
        cp = self._char_pos(0)
        dy = spr.float_offset()
        x = int(pos.x() - cp.x())
        y = int(pos.y() - cp.y() - dy)
        if spr.alpha_at(x, y) > 30:
            return 0 if x < spr.size[0] / 2.0 else 1
        return -1

    def _in_char(self, pos):
        return self._which_char(pos) >= 0

    def _hit(self, pos):
        card = self._card_rect()
        if card.contains(pos):
            return True
        return self._in_char(pos)

    @ui_safe
    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            if self._in_char(e.pos()) or self._collapsed:
                self._show_menu(e.globalPos())
                return
            return
        if e.button() != Qt.LeftButton:
            return
        self._press_pos = QCursor.pos()
        self._press_win = self.pos()
        self._moved = False
        self._drag_ok = self._hit(e.pos())
        if os.environ.get("PEEK_DEBUG_MOUSE") == "1":
            _dbg("press local=%s cursor=%s win=%s drag_ok=%s" %
                 (e.pos(), QCursor.pos(), self.pos(), self._drag_ok))

    def mouseMoveEvent(self, e):
        if self._press_pos is None or not self._drag_ok:
            return
        # 用实时光标位置，避免 Qt 补发的过期 globalPos 把窗口甩出去
        d = QCursor.pos() - self._press_pos
        if not self._moved and (abs(d.x()) + abs(d.y())) > 4:
            self._moved = True
        if self._moved:
            self.move(self._press_win + d)
            if os.environ.get("PEEK_DEBUG_MOUSE") == "1":
                _dbg("move local=%s cursor=%s d=%s new=%s" %
                     (e.pos(), QCursor.pos(), d, self.pos()))

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        was_moved = self._moved
        drag_ok = self._drag_ok
        self._press_pos = None
        self._drag_ok = False
        self._moved = False
        if not drag_ok:
            return
        if not was_moved:
            if self._collapsed:
                self.expand()
            else:
                which = self._which_char(e.pos())
                if which >= 0:
                    self.on_char_click(which)
            return
        if self._collapsed:
            self._save_position()
            return
        # 拖到屏幕边缘附近 → 自动收起成探头；否则把窗口收回到屏幕内，避免只露一半
        if self._near_edge():
            self.collapse()
        else:
            rect = self._clamp_to_screen(QRect(self.pos(), self.size()))
            if rect.topLeft() != self.pos():
                self.move(rect.topLeft())
            self._save_position()

    def _near_edge(self):
        s = self._screen_rect()
        geo = self.geometry()
        card = QRect(geo.x() + CARD.x(), geo.y() + CARD.y(), CARD.width(), CARD.height())
        return (card.left() - s.left() < 30 or s.right() - card.right() < 30 or
                card.top() - s.top() < 30 or s.bottom() - card.bottom() < 26)

    def _show_menu(self, global_pos):
        items = [("恢复窗口" if self._collapsed else "收起为探头",
                  self.expand if self._collapsed else self.collapse),
                 ("打开数据文件夹", self.store.open_folder),
                 ("退出", self.quit_app)]
        self._menu.set_items(items)
        self._menu.show_at(global_pos)

    def _close_menu(self):
        try:
            self._menu.hide()
        except (AttributeError, RuntimeError):
            self._menu = None

    def quit_app(self):
        self._close_menu()
        self._save_position()
        self.store.flush()
        QApplication.quit()

    # ================= Windows 命中测试：透明处不挡鼠标 =================
    def nativeEvent(self, eventType, message):
        try:
            if eventType == b"windows_generic_MSG":
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x0084:      # WM_NCHITTEST
                    # 系统给的是物理像素，Qt 内部是逻辑像素，需要按 DPI 比例换算
                    px = ctypes.c_short(msg.lParam & 0xFFFF).value
                    py = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    dpr = self.devicePixelRatioF() or 1.0
                    local = QPoint(int(round(px / dpr)), int(round(py / dpr))) - self.pos()
                    if not self._hit(local):
                        return True, -1        # HTTRANSPARENT：交给下层窗口
        except Exception:
            pass
        return super().nativeEvent(eventType, message)

    def closeEvent(self, e):
        self._save_position()
        self.store.flush()
        super().closeEvent(e)
