# -*- coding: utf-8 -*-
"""JSON 本地存储：原子写入 + 去抖保存，重启不丢数据。"""
import json
import os
import tempfile
import time
import uuid

from PyQt5.QtCore import QObject, QTimer


def data_dir():
    """数据放在项目 data 目录（便携、方便查看）；目录不可写时退回用户目录。"""
    if os.environ.get("PEEK_PREVIEW") == "1":
        # 离屏自检专用：强制写临时目录，绝不污染真实数据
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        pv = os.path.join(base, "PeekTodoPreview")
        os.makedirs(pv, exist_ok=True)
        return pv
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "data")
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write-test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return path
    except Exception:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path2 = os.path.join(base, "PeekTodo")
        os.makedirs(path2, exist_ok=True)
        return path2


class Store(QObject):
    """待办 / 打卡数据与窗口状态。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path = os.path.join(data_dir(), "data.json")
        self.data = self._load()
        self._dirty = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(260)
        self._timer.timeout.connect(self.flush)

    # ---------- 读写 ----------
    def _default(self):
        return {
            "version": 1,
            "todos": [],
            "habits": [],
            "ui": {"x": None, "y": None, "tab": 0},
        }

    def _load(self):
        d = self._default()
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    d["todos"] = [t for t in loaded.get("todos", []) if isinstance(t, dict)]
                    d["habits"] = [h for h in loaded.get("habits", []) if isinstance(h, dict)]
                    ui = loaded.get("ui") or {}
                    d["ui"].update({k: ui[k] for k in ("x", "y", "tab") if k in ui})
        except Exception as exc:      # 数据损坏时不要让程序起不来
            print("[store] load failed:", exc)
            try:
                if os.path.exists(self.path):
                    os.replace(self.path, self.path + ".broken-%d" % int(time.time()))
            except Exception:
                pass
        return d

    def flush(self):
        if not self._dirty:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
            self._dirty = False
        except Exception as exc:
            print("[store] save failed:", exc)

    def touch(self):
        self._dirty = True
        self._timer.start()

    # ---------- 待办 ----------
    def todos(self):
        return self.data["todos"]

    def add_todo(self, text):
        text = (text or "").strip()
        if not text:
            return None
        item = {"id": uuid.uuid4().hex[:10], "text": text, "done": False,
                "created": time.strftime("%Y-%m-%d %H:%M")}
        self.data["todos"].append(item)
        self.touch()
        return item

    def update_todo(self, tid, text):
        text = (text or "").strip()
        if not text:
            return False
        for t in self.data["todos"]:
            if t.get("id") == tid:
                t["text"] = text
                self.touch()
                return True
        return False

    def toggle_todo(self, tid):
        for t in self.data["todos"]:
            if t.get("id") == tid:
                t["done"] = not t.get("done", False)
                t["done_at"] = time.strftime("%Y-%m-%d %H:%M") if t["done"] else None
                self.touch()
                return t["done"]
        return None

    def delete_todo(self, tid):
        self.data["todos"] = [t for t in self.data["todos"] if t.get("id") != tid]
        self.touch()

    def progress(self):
        todos = self.data["todos"]
        total = len(todos)
        done = sum(1 for t in todos if t.get("done"))
        return done, total

    # ---------- 打卡 ----------
    def habits(self):
        return self.data["habits"]

    def add_habit(self, text):
        text = (text or "").strip()
        if not text:
            return None
        item = {"id": uuid.uuid4().hex[:10], "text": text, "checks": {}}
        self.data["habits"].append(item)
        self.touch()
        return item

    def rename_habit(self, hid, text):
        text = (text or "").strip()
        if not text:
            return False
        for h in self.data["habits"]:
            if h.get("id") == hid:
                h["text"] = text
                self.touch()
                return True
        return False

    def toggle_habit_day(self, hid, day_key):
        for h in self.data["habits"]:
            if h.get("id") == hid:
                checks = h.setdefault("checks", {})
                if checks.get(day_key):
                    checks.pop(day_key, None)
                else:
                    checks[day_key] = True
                self.touch()
                return bool(checks.get(day_key))
        return None

    def delete_habit(self, hid):
        self.data["habits"] = [h for h in self.data["habits"] if h.get("id") != hid]
        self.touch()

    # ---------- 窗口状态 ----------
    def set_ui(self, **kw):
        self.data.setdefault("ui", {}).update(kw)
        self.touch()

    def ui(self):
        return self.data.setdefault("ui", {})

    def open_folder(self):
        os.startfile(data_dir())
