# -*- coding: utf-8 -*-
"""抠图工具重写 · 地基阶段的最小 PyQt6 窗口探针。

⚠ 地基阶段临时产物，由后续架构并入正式结构。
本文件只服务于两件事：验证本机 PyQt6 能创建并显示窗口；充当 PyInstaller 打包探针。
它不属于正式产品代码，正式结构就位后应整体并入或删除。

运行（源码版，用仓库 .venv 的解释器）：
    D:\\workspace\\koutu\\.venv\\Scripts\\python.exe spike\\qt_smoke.py --hold-ms 2500 --shot

运行（打包版）：
    koutu_spike.exe --hold-ms 3000 --shot

说明：
  * 打包版没有控制台，本脚本把结果写成 JSON 日志（默认放 exe 同目录），这是唯一证据来源。
  * --hold-ms 0 表示窗口一直显示到手动关闭；缺省 2500 毫秒后自动退出。
"""

import argparse
import json
import os
import sys
import time
import traceback

APP_TITLE = "抠图工具·地基探针（临时）"


def parse_args(argv):
    parser = argparse.ArgumentParser(description="PyQt6 最小窗口探针（地基阶段临时产物）")
    parser.add_argument("--hold-ms", type=int, default=2500,
                        help="窗口显示多少毫秒后自动退出；0 = 一直显示")
    parser.add_argument("--log", type=str, default=None,
                        help="JSON 日志路径；缺省：打包版=exe 同目录，源码版=spike/_out/")
    parser.add_argument("--shot", action="store_true", help="同时保存窗口截图 PNG（同日志目录）")
    return parser.parse_args(argv)


def default_log_path():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
        return os.path.join(base, "qt_smoke_result.json")
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out")
    return os.path.join(base, "qt_smoke_result.json")


def main(argv):
    args = parse_args(argv)
    t_start = time.perf_counter()
    log_path = args.log or default_log_path()

    result = {
        "运行方式": "打包版(frozen)" if getattr(sys, "frozen", False) else "源码版",
        "启动时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        "PID": os.getpid(),
        "Python": sys.version,
        "可执行文件": sys.executable,
        "工作目录": os.getcwd(),
        "命令行参数": argv,
        "日志路径": log_path,
    }

    def write_result():
        try:
            os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
        except OSError:
            pass  # 打包版没有控制台，写不进去只能放弃（正常情况下不会发生）

    try:
        from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QTimer, Qt
        from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

        t_qt_import = time.perf_counter()
        result["PyQt6 版本"] = PYQT_VERSION_STR
        result["Qt 版本"] = QT_VERSION_STR

        app = QApplication(sys.argv)
        t_app = time.perf_counter()

        window = QMainWindow()
        window.setWindowTitle(APP_TITLE)
        window.resize(520, 340)
        central = QWidget(window)
        layout = QVBoxLayout(central)
        label = QLabel("地基阶段临时产物，由后续架构并入正式结构", central)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        window.setCentralWidget(central)

        state = {"logged": False}

        def finish_log():
            if state["logged"]:
                return
            state["logged"] = True
            t_exposed = time.perf_counter()
            handle = window.windowHandle()
            result["窗口可见(isExposed)"] = bool(handle and handle.isExposed())
            result["脚本启动→导入 PyQt6 完成(ms)"] = round((t_qt_import - t_start) * 1000, 1)
            result["导入完成→QApplication 创建(ms)"] = round((t_app - t_qt_import) * 1000, 1)
            result["QApplication→窗口显示(ms)"] = round((t_exposed - t_app) * 1000, 1)
            result["脚本内总耗时(ms)"] = round((t_exposed - t_start) * 1000, 1)
            if args.shot:
                png = os.path.splitext(log_path)[0] + ".png"
                result["窗口截图"] = png if window.grab().save(png) else "截图保存失败"
            write_result()
            if args.hold_ms > 0:
                QTimer.singleShot(args.hold_ms, app.quit)

        def poll_exposed(attempt=0):
            handle = window.windowHandle()
            if handle and handle.isExposed():
                finish_log()
            elif attempt < 200:  # 约 2 秒上限
                QTimer.singleShot(10, lambda: poll_exposed(attempt + 1))
            else:
                result["窗口可见(isExposed)"] = False
                result["超时说明"] = "2 秒内未等到 isExposed，仍继续显示窗口"
                finish_log()

        window.show()
        QTimer.singleShot(0, poll_exposed)

        rc = app.exec()
        result["退出码"] = rc
        result["正常退出"] = True
        write_result()
        return rc
    except Exception:
        result["异常"] = traceback.format_exc()
        write_result()
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
