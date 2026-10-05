"""入口分发：无参数 → GUI；带参数 → CLI（与 design.md D1/D2 一致）。"""

from __future__ import annotations

import sys


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        from .gui.main_window import launch

        return launch([])
    from .cli.main import main as cli_main

    return cli_main(args)
