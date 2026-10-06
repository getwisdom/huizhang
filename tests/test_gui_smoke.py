"""GUI 冒烟（offscreen）：三页签、去水印占位、参数范围、设置记忆、端到端小样本。"""

import shutil

import helpers
from PyQt6.QtWidgets import QPlainTextEdit

from koutu.gui.main_window import MainWindow


def _mk_window(monkeypatch, tmp_path):
    """把「程序根」指向临时目录后建窗，避免触碰仓库数据目录。"""
    monkeypatch.setattr("koutu.paths.program_root", lambda: tmp_path)
    return MainWindow()


def test_three_tabs_and_watermark_placeholder(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    assert win.tabs.count() == 3
    assert [win.tabs.tabText(i) for i in range(3)] == ["抠图", "排版", "去水印"]

    wm = win.watermark_page
    assert "后续版本提供" in wm.label.text()
    assert wm.btn_start.isEnabled() is False  # 占位禁用态
    assert wm.findChildren(QPlainTextEdit) == []  # 无处理面（不产生任何输出）


def test_cutout_params_paths_and_auto_dirs(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    p = win.cutout_page

    assert p.spin_scan_t.minimum() == 10.0 and p.spin_scan_t.maximum() == 200.0
    assert p.spin_scan_t.value() == 45.0
    assert p.spin_feather.minimum() == 0 and p.spin_feather.maximum() == 20
    assert p.spin_feather.value() == 4

    assert p.ed_src.isReadOnly() and p.ed_dst.isReadOnly()
    assert p.ed_src.text() == str(tmp_path / "原图")
    assert p.ed_dst.text() == str(tmp_path / "底图")
    # 首次启动自动创建「原图」「底图」
    assert (tmp_path / "原图").is_dir() and (tmp_path / "底图").is_dir()


def test_settings_roundtrip(qapp, monkeypatch, tmp_path):
    win = _mk_window(monkeypatch, tmp_path)
    win.cutout_page.spin_scan_t.setValue(60.0)
    win.cutout_page.spin_feather.setValue(6)
    win.tabs.setCurrentIndex(1)
    win.save_settings()
    assert (tmp_path / "koutu.ini").is_file()

    win2 = _mk_window(monkeypatch, tmp_path)
    assert win2.cutout_page.spin_scan_t.value() == 60.0
    assert win2.cutout_page.spin_feather.value() == 6
    assert win2.tabs.currentIndex() == 1
    assert win2.settings.value("ui/geometry") is not None


def test_cutout_end_to_end_offscreen(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("koutu.paths.program_root", lambda: tmp_path)
    helpers.make_badge_image(tmp_path / "原图", "badge.png")
    win = MainWindow()
    page = win.cutout_page

    page.btn_start.click()
    assert not page.btn_start.isEnabled()  # 运行中：禁止再次启动
    win.tabs.setCurrentIndex(2)  # 运行中切页签不得中断任务

    assert helpers.pump_until(qapp, lambda: "完成" in page.status.text())
    text = page.log.toPlainText()
    assert "[完成] badge.png" in text
    assert "全部完成：成功 1 张，失败 0 张" in text
    assert (tmp_path / "底图" / "badge.png").is_file()
    assert (tmp_path / "运行日志.txt").is_file()

    assert helpers.pump_until(qapp, lambda: page.btn_start.isEnabled())  # 恢复可再次运行


def test_layout_end_to_end_offscreen(qapp, monkeypatch, tmp_path, repo_root):
    (tmp_path / "底图").mkdir()
    shutil.copy(repo_root / "排版demo.png", tmp_path / "排版demo.png")
    shutil.copy(repo_root / "golden" / "baseline_products" / "底图" / "1.png", tmp_path / "底图" / "1.png")

    win = _mk_window(monkeypatch, tmp_path)
    page = win.layout_page
    page.btn_start.click()

    assert helpers.pump_until(qapp, lambda: "完成" in page.status.text(), timeout=60.0)
    text = page.log.toPlainText()
    assert "识别到 11 个槽位" in text
    assert "<- 1.png" in text
    assert (tmp_path / "已排版" / "第1页.png").is_file()
    assert (tmp_path / "排版日志.txt").is_file()
