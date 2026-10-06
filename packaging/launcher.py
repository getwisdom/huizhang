"""koutu 打包入口（PyInstaller 顶脚本）：等价于 `python -m koutu`。

说明：PyInstaller 把入口文件当独立脚本做静态分析，`koutu/__main__.py` 里的
相对导入（`from .app import main`）在这种上下文中解析不了；这里改用绝对导入，
并配合 `koutu.spec` 的 pathex（仓库根）完成打包。源码运行仍推荐 `python -m koutu`。
"""

from __future__ import annotations

from koutu import app


def main() -> int:
    return app.main()


if __name__ == "__main__":
    raise SystemExit(main())
