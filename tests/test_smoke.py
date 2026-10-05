"""冒烟示例：只验证测试装置与金标准目录可用（不跑图像处理）。

完整验收（抠图 / 排版 / 去水印 / 打包）见 docs/验收清单.md。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def test_python_version() -> None:
    """Python 版本满足重写项目下限（PyQt6 需要 3.9+）。"""
    assert sys.version_info >= (3, 9), f"需要 Python 3.9+，当前 {sys.version}"


def test_golden_layout(golden_dir: Path) -> None:
    """金标准目录结构就位。"""
    assert (golden_dir / "README.md").is_file()
    assert (golden_dir / "checksums" / "copy_data_after.csv").is_file()
    assert (golden_dir / "baseline_products" / "底图").is_dir()
    assert (golden_dir / "baseline_products" / "已排版" / "第1页.png").is_file()


def test_golden_manifest_rows(golden_dir: Path) -> None:
    """基线清单可读，行数与冻结时一致（66 个数据目录文件）。"""
    csv_path = golden_dir / "checksums" / "copy_data_after.csv"
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 66, f"期望 66 行，实际 {len(rows)}"
    rel_paths = {row["RelPath"] for row in rows}
    assert r"底图\1.png" in rel_paths
    assert r"已排版\第1页.png" in rel_paths
