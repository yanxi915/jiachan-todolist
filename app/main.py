# -*- coding: utf-8 -*-
"""程序入口：高 DPI、单实例保护、启动主窗口。"""
import os
import sys
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
if BASE not in sys.path:
    sys.path.insert(0, BASE)

LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "error.log")
FAULT_FILE = os.path.join(LOG_DIR, "fault.log")
try:
    import faulthandler
    _FAULT_FP = open(FAULT_FILE, "w")
    faulthandler.enable(_FAULT_FP)
except Exception:
    pass


def _log(text):
    """pythonw 没有控制台，异常统一记到 logs/error.log。"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
    except Exception:
        pass


sys.excepthook = lambda tp, val, tb: _log("".join(traceback.format_exception(tp, val, tb)))

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtWidgets import QApplication

from window import PeekWindow

SERVER_KEY = "PeekTodoWidget_SingleInstance_v1"


def _notify_existing():
    """已有实例在跑：唤起它的窗口。必须收到回执才算真的活着（防僵尸进程占坑）。"""
    sock = QLocalSocket()
    sock.connectToServer(SERVER_KEY)
    if not sock.waitForConnected(400):
        return False
    sock.write(b"SHOW")
    sock.flush()
    sock.waitForBytesWritten(400)
    if sock.waitForReadyRead(800) and b"OK" in bytes(sock.readAll()):
        sock.disconnectFromServer()
        return True
    sock.disconnectFromServer()
    return False


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("PeekTodo")
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Microsoft YaHei UI", 9))
    icon_path = os.path.join(ROOT, "assets", "app.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    if _notify_existing():
        return 0

    QLocalServer.removeServer(SERVER_KEY)
    server = QLocalServer()
    server.listen(SERVER_KEY)

    win = PeekWindow(os.path.join(ROOT, "assets"))

    def on_new_connection():
        conn = server.nextPendingConnection()
        if conn is None:
            return
        conn.waitForReadyRead(300)
        data = bytes(conn.readAll())
        if b"SHOW" in data:
            if win._collapsed:
                win.expand()
            win.show()
            win.raise_()
            win.activateWindow()
        conn.write(b"OK")
        conn.flush()
        conn.waitForBytesWritten(300)
        conn.disconnectFromServer()

    server.newConnection.connect(on_new_connection)

    win.show()
    win.raise_()
    return app.exec_()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        _log(traceback.format_exc())
        raise
