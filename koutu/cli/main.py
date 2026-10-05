"""CLI：cutout（抠图）。layout / watermark 在 W2 / W3 接入。

退出码：全部成功 0 / 有文件失败 1 / 未捕获异常 2。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import __version__, paths
from ..core import cutout as cutout_core


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koutu", description="徽章图片处理（抠图 / 去水印 / 排版）"
    )
    parser.add_argument("--version", action="version", version=f"koutu {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<命令>")

    p_cut = sub.add_parser("cutout", help="抠图：原图 → 底图")
    p_cut.add_argument("--src", default=paths.DIR_INPUT, help="输入目录（默认 原图）")
    p_cut.add_argument("--dst", default=paths.DIR_BASE, help="输出目录（默认 底图）")
    p_cut.add_argument("--scan-t", type=float, default=45.0, help="扫描阈值（默认 45）")
    p_cut.add_argument("--feather", type=int, default=4, help="羽化宽度 px（默认 4）")
    p_cut.add_argument("--margin", type=int, default=4, help="裁切边距 px（默认 4）")
    return parser


def _cmd_cutout(args, log_dir=None) -> int:
    root = paths.program_root()
    src = paths.resolve_dir(root, args.src)
    dst = paths.resolve_dir(root, args.dst)
    log_root = Path(log_dir) if log_dir else root
    summary, _text = cutout_core.run_cutout_batch(
        src,
        dst,
        scan_t=args.scan_t,
        feather=args.feather,
        margin=args.margin,
        log_path=log_root / paths.LOG_CUTOUT,
        emit=lambda line: print(line),
    )
    return 0 if summary.fail == 0 and not summary.cancelled else 1


def main(argv=None, log_dir=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        if args.command == "cutout":
            return _cmd_cutout(args, log_dir=log_dir)
        print(f"错误：尚未实现的子命令 {args.command}")
        return 2
    except Exception as exc:  # 未捕获异常 → 退出码 2
        print(f"发生错误: {exc}")
        return 2
