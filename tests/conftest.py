"""pytest 共享夹具（重写项目验收装置骨架）。

说明：本骨架只提供最基础能力；完整验收流程见 docs/验收清单.md。
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COPY_ROOT = Path(r"D:\workspace\_koutu_golden")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录。"""
    return REPO_ROOT


@pytest.fixture(scope="session")
def golden_dir(repo_root: Path) -> Path:
    """金标准冻结目录（golden/）。"""
    return repo_root / "golden"


@pytest.fixture(scope="session")
def copy_root() -> Path:
    """仓库外金标准副本；不存在时跳过依赖它的用例。"""
    if not COPY_ROOT.exists():
        pytest.skip("仓库外副本 D:\\workspace\\_koutu_golden 不存在，跳过副本相关用例")
    return COPY_ROOT
