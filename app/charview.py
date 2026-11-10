# -*- coding: utf-8 -*-
"""角色绘制：原图「两位角色并排」整体贴图 + 缓慢上下漂浮 + 随机眨眼。

不拆开角色：三张原图各取一整块（两位角色保持原图里的并排关系）。
眨眼不用任何色块遮眼：把「笑颜」那张原图里真实的闭眼小块羽化后贴回去。
"""
import json
import math
import os
import random

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QImage, QPixmap


class CharacterPair(object):
    def __init__(self, assets_dir, phase=0.0):
        with open(os.path.join(assets_dir, "meta.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.size = tuple(meta["sprite"])
        self.items = []
        for e in meta["expressions"]:
            pm = QPixmap(os.path.join(assets_dir, e["file"]))
            self.items.append({
                "id": e["id"],
                "pixmap": pm,
                "image": pm.toImage().convertToFormat(QImage.Format_ARGB32),
            })

        self.index = 0
        self._t = phase
        self._blink_t = None
        self._next_blink = random.uniform(1.4, 3.6)
        self._blink_clock = 0.0

        # 闭眼贴片：从「笑颜」原图裁下四只眼睛周围的小块，四边羽化
        self._patches = []
        happy = None
        for it in self.items:
            if it["id"] == "happy":
                happy = it["pixmap"]
        no_blink = meta.get("no_blink") or {}
        if happy is not None:
            for e in meta["eyes"]:
                ex, ey, ew, eh = e["box"]
                pad = 5
                rx = max(0, ex - pad)
                ry = max(0, ey - pad)
                rw = min(self.size[0] - rx, ew + pad * 2)
                rh = min(self.size[1] - ry, eh + pad * 2)
                patch = happy.copy(rx, ry, rw, rh)
                self._patches.append((rx, ry, _feather(patch, pad), e.get("owner", "l")))
        self._no_blink = {k: set(v) for k, v in no_blink.items()}

    # ---------- 状态 ----------
    @property
    def expr_id(self):
        return self.items[self.index]["id"]

    def next_expression(self):
        self.index = (self.index + 1) % len(self.items)
        return self.index

    def set_index(self, i):
        self.index = i % len(self.items)

    @property
    def pixmap(self):
        return self.items[self.index]["pixmap"]

    def alpha_at(self, x, y):
        img = self.items[self.index]["image"]
        if x < 0 or y < 0 or x >= img.width() or y >= img.height():
            return 0
        return img.pixelColor(int(x), int(y)).alpha()

    def float_offset(self):
        return math.sin(self._t) * 3.0

    def tick(self, dt):
        """推进动画；返回 True 表示需要重绘。"""
        self._t += dt * (2.0 * math.pi / 5.6)

        self._blink_clock += dt
        need = False
        if self._blink_t is None and self._blink_clock >= self._next_blink:
            self._blink_t = 0.0
            self._blink_clock = 0.0
            need = True
        if self._blink_t is not None:
            self._blink_t += dt / 0.16
            if self._blink_t >= 1.0:
                self._blink_t = None
                self._next_blink = (random.uniform(1.6, 2.6)
                                    if random.random() < 0.22 else random.uniform(2.8, 7.0))
                self._blink_clock = 0.0
            need = True
        return need

    def blink_amount(self):
        t = self._blink_t
        if t is None:
            return 0.0
        k = t / 0.45 if t < 0.45 else (1.0 - t) / 0.55
        return max(0.0, min(1.0, k))

    # ---------- 绘制 ----------
    def paint(self, painter, pos, dy=0.0):
        painter.drawPixmap(QPointF(pos.x(), pos.y() + dy), self.pixmap)
        if not self._patches:
            return
        if self.blink_amount() <= 0.16:
            return
        cur = self.expr_id
        for (rx, ry, patch, owner) in self._patches:
            if cur in self._no_blink.get(owner, ()):
                continue
            painter.drawPixmap(QPointF(pos.x() + rx, pos.y() + dy + ry), patch)


def _feather(pm, pad):
    """把贴片四边 alpha 线性羽化，避免矩形硬边留下接缝。"""
    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    if w < 3 or h < 3 or pad < 1:
        return pm
    for y in range(h):
        k = min(1.0, y / float(pad), (h - 1 - y) / float(pad))
        for x in range(w):
            kx = min(k, x / float(pad), (w - 1 - x) / float(pad))
            if kx >= 1.0:
                continue
            c = img.pixelColor(x, y)
            c.setAlpha(int(c.alpha() * kx))
            img.setPixelColor(x, y, c)
    return QPixmap.fromImage(img)
