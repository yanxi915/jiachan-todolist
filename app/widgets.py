# -*- coding: utf-8 -*-
"""自绘控件集合：图标按钮 / 标签栏 / 待办行 / 打卡行 / 内联输入 / 气泡 / 新增按钮。

全部手绘，不使用系统原生按钮，也没有粗边框。
"""
from PyQt5.QtCore import (QEasingCurve, QPoint, QPointF, QRect, QRectF, QSize, Qt,
                          QVariantAnimation, pyqtSignal)
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QAbstractButton, QLineEdit, QWidget

from theme import (BLUSH, CREAM, INK, INK_SOFT, LINE, LINE_SOFT, MENU_BG, MUTED, NAVY,
                   NAVY_DEEP, PINK, ROW_BG, ROW_BG_DONE, ROW_GAP, ROW_H, STROKE, STROKE_DOT,
                   SURFACE, TAB_BG, draw_check, draw_cross, font, hairline, qc)


class IconButton(QAbstractButton):
    """手绘图标按钮：最小化 / 关闭 / 加号 / 删除。"""

    def __init__(self, kind, size=22, parent=None, tone="neutral"):
        super().__init__(parent)
        self.kind = kind
        self.tone = tone
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        if self._hover:
            col = qc("#D98384", 30) if self.tone == "danger" else qc("#FFFFFF", 46)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawEllipse(r.adjusted(1, 1, -1, -1))
        col = PINK if (self._hover and self.tone == "danger") else (INK if self._hover else INK_SOFT)
        pen = QPen(col)
        pen.setWidthF(1.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cx, cy = r.center().x() + 0.5, r.center().y() + 0.5
        s = min(r.width(), r.height())
        if self.kind == "min":
            p.drawLine(QPointF(cx - s * 0.26, cy + 1), QPointF(cx + s * 0.26, cy + 1))
        elif self.kind == "close":
            k = s * 0.21
            p.drawLine(QPointF(cx - k, cy - k + 1), QPointF(cx + k, cy + k + 1))
            p.drawLine(QPointF(cx - k, cy + k + 1), QPointF(cx + k, cy - k + 1))
        elif self.kind == "plus":
            k = s * 0.26
            p.drawLine(QPointF(cx - k, cy), QPointF(cx + k, cy))
            p.drawLine(QPointF(cx, cy - k), QPointF(cx, cy + k))


class TabBar(QWidget):
    """待办 / 已完成 / 打卡：胶囊形选中块，切换有短动画。"""

    currentChanged = pyqtSignal(int)
    LABELS = ("待办", "已完成", "打卡")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)
        self._index = 0
        self._pill = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, v):
        self._pill = float(v)
        self.update()

    def set_index(self, i, animate=True):
        if i == self._index and abs(self._pill - i) < 0.01:
            return
        self._index = i
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._pill)
            self._anim.setEndValue(float(i))
            self._anim.start()
        else:
            self._pill = float(i)
            self.update()

    def index(self):
        return self._index

    def _seg_w(self):
        return (self.width() - 8) / 3.0

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(self.rect()).adjusted(0, 0, 0, 0)
        p.setPen(Qt.NoPen)
        p.setBrush(TAB_BG)
        p.drawRoundedRect(r, 16, 16)

        sw = self._seg_w()
        x = 4 + self._pill * sw
        pill = QRectF(x, 4, sw, 24)
        p.setBrush(qc("#FCFEFF"))
        p.drawRoundedRect(pill, 12, 12)
        p.setPen(QPen(LINE_SOFT, 1))
        p.drawRoundedRect(pill.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)

        for i, label in enumerate(self.LABELS):
            rect = QRectF(4 + i * sw, 4, sw, 24)
            active = (i == self._index)
            f = font(12, QFont.DemiBold if active else QFont.Normal)
            p.setFont(f)
            p.setPen(INK if active else MUTED)
            p.drawText(rect, Qt.AlignCenter, label)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        sw = self._seg_w()
        idx = int((e.pos().x() - 4) // sw)
        idx = max(0, min(2, idx))
        if idx != self._index:
            self.set_index(idx)
            self.currentChanged.emit(idx)


class TaskRow(QWidget):
    """一条待办：胶囊底色 + 左侧空心圆 + 常驻删除按钮，双击文字可改写。"""

    toggled = pyqtSignal(str)
    deleted = pyqtSignal(str)
    renamed = pyqtSignal(str, str)

    def __init__(self, todo, parent=None):
        super().__init__(parent)
        self.tid = todo["id"]
        self.text = todo.get("text", "")
        self.done = bool(todo.get("done"))
        self.setFixedHeight(ROW_H)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self._hover_del = False
        self._editor = None
        self._fade = 0.0

    # ---- 尺寸 ----
    def _circle(self):
        h = self.height()
        return QRectF(12, (h - 17) / 2.0, 17, 17)

    def _del_rect(self):
        h = self.height()
        return QRectF(self.width() - 30, (h - 20) / 2.0, 20, 20)

    def _text_rect(self):
        h = self.height()
        return QRectF(37, 0, self.width() - 37 - 34, h)

    # ---- 绘制 ----
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(ROW_BG_DONE if self.done else ROW_BG)
        p.drawRoundedRect(r, ROW_H / 2.0, ROW_H / 2.0)
        hairline(p, r, ROW_H / 2.0, LINE_SOFT, 1.0)

        c = self._circle()
        if self.done:
            p.setPen(Qt.NoPen)
            p.setBrush(NAVY)
            p.drawEllipse(c)
            draw_check(p, c.adjusted(1.5, 1.5, -1.5, -1.5), QColor(255, 255, 255), 1.5)
        else:
            p.setPen(QPen(STROKE_DOT, 1.3))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(c.adjusted(0.4, 0.4, -0.4, -0.4))

        if self._editor is None:
            f = font(12, QFont.Normal)
            f.setStrikeOut(self.done)
            p.setFont(f)
            p.setPen(MUTED if self.done else INK)
            fm = QFontMetrics(f)
            txt = fm.elidedText(self.text, Qt.ElideRight, int(self._text_rect().width()))
            p.drawText(self._text_rect(), Qt.AlignVCenter | Qt.AlignLeft, txt)

        if self._hover_del:
            p.setPen(Qt.NoPen)
            p.setBrush(qc("#D98384", 30))
            p.drawEllipse(self._del_rect().adjusted(2, 2, -2, -2))
        draw_cross(p, self._del_rect(), PINK if self._hover_del else STROKE_DOT, 1.35)

    # ---- 交互 ----
    def mouseMoveEvent(self, e):
        hover = self._del_rect().contains(QPointF(e.pos()))
        if hover != self._hover_del:
            self._hover_del = hover
            self.setCursor(Qt.PointingHandCursor if hover else Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self._hover_del = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        pos = QPointF(e.pos())
        if self._del_rect().adjusted(-4, -4, 4, 4).contains(pos):
            self.deleted.emit(self.tid)
            return
        if self._circle().adjusted(-6, -6, 6, 6).contains(pos):
            self.toggled.emit(self.tid)
            return

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton and self._text_rect().contains(QPointF(e.pos())):
            self.start_edit()

    # ---- 内联改名 ----
    def start_edit(self):
        if self._editor is not None:
            return
        ed = QLineEdit(self.text, self)
        ed.setGeometry(QRect(34, (self.height() - 30) // 2, self.width() - 34 - 32, 30))
        ed.setFont(font(12))
        ed.setStyleSheet(
            "QLineEdit{background:rgba(255,255,255,225);border:1px solid rgba(42,55,82,80);"
            "border-radius:13px;padding-left:10px;color:#16344F;selection-background-color:#2E5F8E;}"
        )
        ed.returnPressed.connect(self._commit_edit)
        ed.editingFinished.connect(self._commit_edit)
        ed.installEventFilter(self)
        ed.selectAll()
        ed.show()
        ed.setFocus()
        self._editor = ed
        self.update()

    def _close_edit(self):
        if self._editor is not None:
            self._editor.hide()
            self._editor.deleteLater()
            self._editor = None
            self.update()

    def _commit_edit(self):
        if self._editor is None:
            return
        text = self._editor.text().strip()
        self._close_edit()
        if text and text != self.text:
            self.text = text
            self.renamed.emit(self.tid, text)
        else:
            self.update()

    def eventFilter(self, obj, ev):
        if self._editor is not None and obj is self._editor:
            if ev.type() == ev.KeyPress and ev.key() == Qt.Key_Escape:
                self._close_edit()
                return True
        return super().eventFilter(obj, ev)


class HabitRow(QWidget):
    """一条打卡习惯：标题 + 周一到周日 7 个独立小胶囊 + 删除按钮。"""

    day_toggled = pyqtSignal(str, str)
    deleted = pyqtSignal(str)
    renamed = pyqtSignal(str, str)

    CHIP = 21
    CHIP_GAP = 5

    def __init__(self, habit, days, parent=None):
        super().__init__(parent)
        self.hid = habit["id"]
        self.text = habit.get("text", "")
        self.checks = dict(habit.get("checks") or {})
        self.days = days                     # [(label, key, is_today), ...]
        self.setFixedHeight(58)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self._hover_del = False
        self._editor = None

    def _del_rect(self):
        return QRectF(self.width() - 30, 9, 20, 20)

    def _chip_rect(self, i):
        x = 13 + i * (self.CHIP + self.CHIP_GAP)
        return QRectF(x, 31, self.CHIP, self.CHIP)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(ROW_BG)
        p.drawRoundedRect(r, 16, 16)
        hairline(p, r, 16, LINE_SOFT, 1.0)

        if self._editor is None:
            f = font(12, QFont.DemiBold)
            p.setFont(f)
            p.setPen(INK)
            fm = QFontMetrics(f)
            title = fm.elidedText(self.text, Qt.ElideRight, self.width() - 60)
            p.drawText(QRectF(13, 8, self.width() - 56, 18), Qt.AlignVCenter | Qt.AlignLeft, title)

        for i, (label, key, is_today) in enumerate(self.days):
            cr = self._chip_rect(i)
            on = bool(self.checks.get(key))
            if on:
                p.setPen(Qt.NoPen)
                p.setBrush(NAVY)
                p.drawEllipse(cr)
                if is_today:
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(BLUSH, 1.2))
                    p.drawEllipse(cr.adjusted(-1.6, -1.6, 1.6, 1.6))
            else:
                p.setBrush(qc("#FFFFFF", 190))
                p.setPen(QPen(BLUSH if is_today else qc("#A7C0D2"), 1.2))
                p.drawEllipse(cr)
            f = font(10, QFont.DemiBold if on else QFont.Normal)
            p.setFont(f)
            p.setPen(QColor(255, 255, 255) if on else (INK_SOFT if is_today else MUTED))
            p.drawText(cr, Qt.AlignCenter, label)

        if self._hover_del:
            p.setPen(Qt.NoPen)
            p.setBrush(qc("#D98384", 30))
            p.drawEllipse(self._del_rect().adjusted(2, 2, -2, -2))
        draw_cross(p, self._del_rect(), PINK if self._hover_del else STROKE_DOT, 1.35)

    def mouseMoveEvent(self, e):
        hover = self._del_rect().contains(QPointF(e.pos()))
        if hover != self._hover_del:
            self._hover_del = hover
            self.update()

    def leaveEvent(self, e):
        self._hover_del = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        pos = QPointF(e.pos())
        if self._del_rect().adjusted(-4, -4, 4, 4).contains(pos):
            self.deleted.emit(self.hid)
            return
        for i, (label, key, is_today) in enumerate(self.days):
            if self._chip_rect(i).adjusted(-2, -2, 2, 2).contains(pos):
                self.day_toggled.emit(self.hid, key)
                return

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton and QRectF(10, 4, self.width() - 44, 22).contains(QPointF(e.pos())):
            self.start_edit()

    def start_edit(self):
        if self._editor is not None:
            return
        ed = QLineEdit(self.text, self)
        ed.setGeometry(QRect(11, 6, self.width() - 46, 24))
        ed.setFont(font(12))
        ed.setStyleSheet(
            "QLineEdit{background:rgba(255,255,255,235);border:1px solid rgba(42,55,82,80);"
            "border-radius:11px;padding-left:8px;color:#16344F;}"
        )
        ed.returnPressed.connect(self._commit_edit)
        ed.editingFinished.connect(self._commit_edit)
        ed.installEventFilter(self)
        ed.selectAll()
        ed.show()
        ed.setFocus()
        self._editor = ed
        self.update()

    def _close_edit(self):
        if self._editor is not None:
            self._editor.hide()
            self._editor.deleteLater()
            self._editor = None
            self.update()

    def _commit_edit(self):
        if self._editor is None:
            return
        text = self._editor.text().strip()
        self._close_edit()
        if text and text != self.text:
            self.text = text
            self.renamed.emit(self.hid, text)
        else:
            self.update()

    def eventFilter(self, obj, ev):
        if self._editor is not None and obj is self._editor:
            if ev.type() == ev.KeyPress and ev.key() == Qt.Key_Escape:
                self._close_edit()
                return True
        return super().eventFilter(obj, ev)


class InlineInput(QWidget):
    """新增待办 / 打卡时的内联输入框（回车提交，Esc 取消）。"""

    submitted = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, placeholder, height=36, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.edit = QLineEdit(self)
        self.edit.setGeometry(QRect(14, (height - 24) // 2, self.width() - 28, 24))
        self.edit.setPlaceholderText(placeholder)
        self.edit.setFont(font(12))
        self.edit.setStyleSheet(
            "QLineEdit{background:transparent;border:none;color:#16344F;"
            "selection-background-color:#2E5F8E;selection-color:#FFFFFF;}"
            "QLineEdit::placeholder{color:#B1A899;}"
        )
        self.edit.returnPressed.connect(self._submit)
        self.edit.installEventFilter(self)

    def resizeEvent(self, e):
        self.edit.setGeometry(QRect(14, (self.height() - 24) // 2, self.width() - 28, 24))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(qc("#FFFFFF", 200))
        p.drawRoundedRect(r, r.height() / 2.0, r.height() / 2.0)
        p.setPen(QPen(NAVY if self.edit.hasFocus() else LINE_SOFT, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, r.height() / 2.0, r.height() / 2.0)
        p.setPen(QPen(STROKE_DOT, 1.3))
        cx, cy = 20, r.center().y()
        p.drawLine(QPointF(cx - 5, cy), QPointF(cx + 5, cy))
        p.drawLine(QPointF(cx, cy - 5), QPointF(cx, cy + 5))

    def eventFilter(self, obj, ev):
        if obj is self.edit:
            if ev.type() == ev.KeyPress and ev.key() == Qt.Key_Escape:
                self.cancelled.emit()
                return True
        return super().eventFilter(obj, ev)

    def _submit(self):
        text = self.edit.text().strip()
        self.submitted.emit(text)

    def focus(self):
        self.edit.setFocus()

    def clear(self):
        self.edit.clear()


class AddButton(QWidget):
    """底部「新增待办 / 新增打卡」按钮（手绘胶囊，无原生边框）。"""

    clicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self._hover = False

    def set_text(self, text):
        if text != self.text:
            self.text = text
            self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(qc("#FFFFFF", 210) if not self._hover else qc("#FFFFFF", 245))
        p.drawRoundedRect(r, r.height() / 2.0, r.height() / 2.0)
        p.setPen(QPen(STROKE if self._hover else LINE_SOFT, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, r.height() / 2.0, r.height() / 2.0)

        # 加号圆圈
        cx = 30
        cy = r.center().y()
        rad = 9
        p.setPen(Qt.NoPen)
        p.setBrush(NAVY if self._hover else qc("#2E5F8E", 220))
        p.drawEllipse(QPointF(cx, cy), rad, rad)
        p.setPen(QPen(QColor(255, 255, 255), 1.6))
        p.drawLine(QPointF(cx - 4, cy), QPointF(cx + 4, cy))
        p.drawLine(QPointF(cx, cy - 4), QPointF(cx, cy + 4))

        f = font(12, QFont.DemiBold if self._hover else QFont.Normal)
        p.setFont(f)
        p.setPen(INK if self._hover else INK_SOFT)
        p.drawText(QRectF(44, 0, r.width() - 50, r.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


class BubblePainter(object):
    """角色台词气泡的度量与绘制（由主窗口直接画在透明层上，保证刷新可靠）。"""

    @staticmethod
    def measure(text, max_width=196):
        f = font(12)
        fm = QFontMetrics(f)
        br = fm.boundingRect(QRect(0, 0, max_width - 24, 400), Qt.TextWordWrap, text)
        w = min(max_width, max(66, br.width() + 24))
        h = max(34, br.height() + 20)
        return QSize(int(w), int(h + 11))

    @staticmethod
    def draw(p, rect, text, tip_x=None):
        body = QRectF(rect).adjusted(0, 0, 0, -11)
        path = QPainterPath()
        path.addRoundedRect(body, 14, 14)
        # 底部小尾巴，指向说话的角色
        tx = rect.left() + 22 if tip_x is None else tip_x
        tx = max(body.left() + 16.0, min(float(tx), body.right() - 24.0))
        tail = QPainterPath()
        tail.moveTo(tx - 14, body.bottom() - 2)
        tail.lineTo(tx, QRectF(rect).bottom() - 1)
        tail.lineTo(tx + 18, body.bottom() - 1)
        tail.closeSubpath()
        path = path.united(tail)

        p.setPen(Qt.NoPen)
        p.setBrush(qc("#221F26", 24))
        p.drawPath(path.translated(0, 1.5))
        p.setBrush(qc("#F6FBFE", 252))
        p.drawPath(path)
        p.setPen(QPen(qc("#6E93AF", 70), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        p.setPen(INK)
        p.setFont(font(12))
        p.drawText(body.adjusted(12, 9, -12, -9), Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter,
                   text)
