"""GUI 目录选择（flexible-io）：可编辑/记忆/运行锁定/五连校验/打开跟随/关窗保护。

全程 offscreen；窗口一律把「程序根」指向临时目录，避免触碰仓库数据目录。
"""

import shutil
from pathlib import Path

import helpers
from PyQt6.QtCore import QTimer

from koutu.gui.main_window import MainWindow


def _mk_window(monkeypatch, tmp_path):
    """把「程序根」指向临时目录后建窗，避免触碰仓库数据目录。"""
    monkeypatch.setattr("koutu.paths.program_root", lambda: tmp_path)
    return MainWindow()


def _unused_drive():
    """找一个本机不存在的盘符（如不存在则返回 None）。"""
    for letter in "QRSTUVWXYZ":
        if not Path(f"{letter}:\\").exists():
            return letter + ":"
    return None


class _WarningBox:
    """替身 QMessageBox：只记录 warning 调用（模态对话框在 offscreen 下无法真实交互）。"""

    calls: list = []

    @staticmethod
    def warning(parent, title, text):
        _WarningBox.calls.append((title, text))


def _capture_warnings(monkeypatch):
    _WarningBox.calls = []
    monkeypatch.setattr("koutu.gui.main_window.QMessageBox", _WarningBox)
    return _WarningBox.calls


def _drive_dialog(qapp, action: str):
    """定时器驱动：等模态对话框出现后点击指定按钮；返回 {texts, clicked}。"""
    state = {"texts": None, "clicked": False}

    def _act():
        dlg = qapp.activeModalWidget()
        if dlg is None:
            QTimer.singleShot(30, _act)
            return
        buttons = dlg.buttons()
        state["texts"] = [b.text() for b in buttons]
        for b in buttons:
            if b.text() == action:
                b.click()
                state["clicked"] = True
                return
        QTimer.singleShot(30, _act)

    QTimer.singleShot(30, _act)
    return state


def _stage_layout(tmp_path, repo_root, n: int):
    """布置可运行的最小排版现场：真模板 + n 张合成底图（合成图更快）。"""
    (tmp_path / "底图").mkdir()
    shutil.copy(repo_root / "排版demo.png", tmp_path / "排版demo.png")
    for i in range(1, n + 1):
        helpers.make_badge_image(
            tmp_path / "底图", f"{i:02d}.png", size=200, cx=100, cy=100, r=60
        )


# --------------------------------------------------------------- 目录行与记忆
def test_dir_rows_defaults_editable(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    p = win.cutout_page
    assert not p.ed_src.edit.isReadOnly() and not p.ed_dst.edit.isReadOnly()
    assert p.ed_src.text() == str(tmp_path / "原图")
    assert p.ed_dst.text() == str(tmp_path / "底图")
    assert win.layout_page.ed_src.text() == str(tmp_path / "底图")
    assert win.layout_page.ed_dst.text() == str(tmp_path / "已排版")
    assert win.layout_page.ed_demo.isReadOnly()  # 模板行保持只读
    # 浏览/恢复默认按钮齐备
    for row in (p.ed_src, p.ed_dst):
        assert row.btn_browse.text() == "浏览…" and row.btn_reset.text() == "恢复默认"


def test_dir_memory_and_fallback(qapp, monkeypatch, tmp_path):
    (tmp_path / "自定义 输入").mkdir()
    (tmp_path / "自定义 输出").mkdir()
    win = _mk_window(monkeypatch, tmp_path)
    win.cutout_page.ed_src.edit.setText(str(tmp_path / "自定义 输入"))
    win.cutout_page.ed_dst.edit.setText("自定义 输出")  # 相对路径按程序根解析
    win.save_settings()

    win2 = _mk_window(monkeypatch, tmp_path)
    assert win2.cutout_page.ed_src.text() == str(tmp_path / "自定义 输入")
    assert win2.cutout_page.ed_dst.text() == "自定义 输出"
    assert win2.cutout_page.ed_dst.value() == tmp_path / "自定义 输出"

    # 记忆目录不可用 → 回退默认 + 中文提示（状态行与日志）
    win2.cutout_page.ed_src.edit.setText(str(tmp_path / "已删除的目录"))
    win2.save_settings()
    win3 = _mk_window(monkeypatch, tmp_path)
    assert win3.cutout_page.ed_src.text() == str(tmp_path / "原图")
    assert "已恢复默认" in win3.cutout_page.status.text()
    assert "已恢复默认" in win3.cutout_page.log.toPlainText()


def test_dir_reset_button(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    row = win.cutout_page.ed_dst
    row.edit.setText("D:\\随便一个目录")
    row.btn_reset.click()
    assert row.text() == str(tmp_path / "底图")


# ------------------------------------------------------------- 「打开输出目录」
def test_open_output_follows_selection(qapp, monkeypatch, tmp_path):
    opened = []

    class _FakeDesktop:
        @staticmethod
        def openUrl(url):
            opened.append(url.toLocalFile())

    monkeypatch.setattr("koutu.gui.main_window.QDesktopServices", _FakeDesktop)
    win = _mk_window(monkeypatch, tmp_path)

    # 默认输出目录：不存在时创建后打开
    win.cutout_page.btn_open.click()
    assert (tmp_path / "底图").is_dir()
    assert opened and Path(opened[-1]) == tmp_path / "底图"

    # 自定义（中文 + 空格）：父目录存在 → 只创建最后一级后打开
    (tmp_path / "项目甲").mkdir()
    custom = tmp_path / "项目甲" / "出图 目录"
    win.cutout_page.ed_dst.edit.setText(str(custom))
    win.cutout_page.btn_open.click()
    assert custom.is_dir()
    assert Path(opened[-1]) == custom


# --------------------------------------------------------------- 校验五连
def test_validation_five_cn_errors_no_start(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    calls = _capture_warnings(monkeypatch)
    page = win.cutout_page

    # ① 输入目录不存在（GUI 不自动创建自定义输入目录）
    page.ed_src.edit.setText(str(tmp_path / "不存在的输入"))
    page.btn_start.click()
    assert calls and "输入目录不存在" in calls[-1][1]
    assert win._thread is None and page.btn_start.isEnabled()
    assert not (tmp_path / "不存在的输入").exists()

    # ② 输出目录不存在且无法创建（父目录缺失）
    page.ed_src.edit.setText(str(tmp_path / "原图"))
    page.ed_dst.edit.setText(str(tmp_path / "没有父目录" / "新底图"))
    page.btn_start.click()
    assert "无法创建" in calls[-1][1]
    assert win._thread is None and not (tmp_path / "没有父目录").exists()

    # ③ 盘符不存在
    unused = _unused_drive()
    if unused:
        page.ed_dst.edit.setText(f"{unused}\\出图")
        page.btn_start.click()
        assert "盘符不存在" in calls[-1][1]
        assert win._thread is None

    # ④ 输出目录与输入目录相同
    page.ed_dst.edit.setText(str(tmp_path / "原图"))
    page.btn_start.click()
    assert "不能和输入目录相同" in calls[-1][1]
    assert win._thread is None

    # ⑤ 路径过长（超过 259 字符）
    page.ed_dst.edit.setText(str(tmp_path / ("超长" * 140)))
    page.btn_start.click()
    assert "路径过长（超过 259 字符）" in calls[-1][1]
    assert win._thread is None

    # 五条均为中文文案：不直出 WinError / 英文异常原文
    assert calls, "应至少产生校验提示"
    for _title, text in calls:
        assert "WinError" not in text and "[Errno" not in text and "Error" not in text


def test_validation_writable_probe(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    calls = _capture_warnings(monkeypatch)
    monkeypatch.setattr("koutu.gui.dirselect.probe_writable", lambda d: False)
    page = win.cutout_page

    page.btn_start.click()
    assert calls and "没有写入权限" in calls[-1][1]
    assert win._thread is None


def test_creation_rule_last_level_only(tmp_path):
    from koutu.gui import dirselect

    (tmp_path / "父").mkdir()
    ok = dirselect.validate_task_dirs(tmp_path / "父", tmp_path / "父" / "新输出", root=tmp_path)
    assert ok is None
    assert (tmp_path / "父" / "新输出").is_dir()

    err = dirselect.validate_task_dirs(
        tmp_path / "父", tmp_path / "缺父" / "子" / "输出", root=tmp_path
    )
    assert err and "无法创建" in err
    assert not (tmp_path / "缺父").exists()


# --------------------------------------------------------------- 运行锁定与提示
def test_runtime_lock_dir_rows(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("koutu.paths.program_root", lambda: tmp_path)
    helpers.make_badge_image(tmp_path / "原图", "badge.png")
    win = MainWindow()
    page = win.cutout_page

    page.btn_start.click()
    assert not page.ed_src.isEnabled() and not page.ed_dst.isEnabled()
    assert not page.ed_dst.btn_browse.isEnabled() and not page.ed_dst.btn_reset.isEnabled()
    assert not win.layout_page.ed_src.isEnabled()

    assert helpers.pump_until(qapp, lambda: page.btn_start.isEnabled())
    assert page.ed_src.isEnabled() and page.ed_dst.btn_browse.isEnabled()


def test_prerun_hint_shows_in_status(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    win._on_log_line(win.cutout_page, "运行前: 输入 3 张；同名覆盖 1 个；抠图不清理输出目录")
    assert "运行前: 输入 3 张" in win.cutout_page.status.text()
    assert "运行前: 输入 3 张" in win.cutout_page.log.toPlainText()


# --------------------------------------------------------------- 自定义输出（GUI）
def test_layout_custom_dst_keeps_files(qapp, monkeypatch, tmp_path, repo_root):
    (tmp_path / "底图").mkdir()
    shutil.copy(repo_root / "排版demo.png", tmp_path / "排版demo.png")
    shutil.copy(
        repo_root / "golden" / "baseline_products" / "底图" / "1.png",
        tmp_path / "底图" / "1.png",
    )
    custom = tmp_path / "自定义 输出"
    custom.mkdir()
    (custom / "我的照片.png").write_bytes(b"user")

    win = _mk_window(monkeypatch, tmp_path)
    page = win.layout_page
    page.ed_dst.edit.setText(str(custom))
    page.btn_start.click()
    assert helpers.pump_until(qapp, lambda: "完成" in page.status.text(), timeout=60.0)

    text = page.log.toPlainText()
    assert "自定义输出目录，不清理" in text
    assert (custom / "我的照片.png").is_file()
    assert (custom / "第1页.png").is_file()


# --------------------------------------------------------------- 关窗保护（P0-3）
def test_close_during_task_quit_cancels_and_closes(qapp, monkeypatch, tmp_path, repo_root):
    """运行中关窗 → 中文确认；选「取消任务并退出」→ 取消收束后关闭，不崩溃。"""
    _stage_layout(tmp_path, repo_root, n=22)
    win = _mk_window(monkeypatch, tmp_path)
    win.show()
    page = win.layout_page
    page.btn_start.click()
    assert not page.btn_start.isEnabled()

    state = _drive_dialog(qapp, "取消任务并退出")
    win.close()  # closeEvent 弹中文确认；定时器在嵌套事件循环里点击

    assert state["clicked"], "关窗确认对话框未出现或未被点击"
    assert state["texts"] is not None
    assert set(state["texts"]) == {"继续等待", "取消任务并退出"}
    assert helpers.pump_until(qapp, lambda: not win.isVisible(), timeout=60.0), (
        "取消收束后窗口未关闭"
    )
    assert win._thread is None
    assert "已取消" in page.log.toPlainText()  # 边界收束：日志含取消状态行


def test_close_during_task_wait_keeps_window(qapp, monkeypatch, tmp_path, repo_root):
    """选「继续等待」→ 窗口保持、任务照常完成，随后可正常关闭。"""
    _stage_layout(tmp_path, repo_root, n=11)
    win = _mk_window(monkeypatch, tmp_path)
    win.show()
    page = win.layout_page
    page.btn_start.click()

    state = _drive_dialog(qapp, "继续等待")
    win.close()
    assert state["clicked"]
    assert win.isVisible()  # 继续等待：窗口未关闭

    assert helpers.pump_until(qapp, lambda: page.btn_start.isEnabled(), timeout=60.0)
    assert "完成" in page.status.text()
    win.close()
    assert not win.isVisible()


def test_close_without_task_ok(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    win.show()
    win.close()
    assert not win.isVisible()
