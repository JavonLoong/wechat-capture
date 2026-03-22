# -*- coding: utf-8 -*-
"""
wechat_capture.cli — 统一命令行入口

用法:
  wechat-capture screenshot <联系人名>  [--output-dir ./output]
  wechat-capture database   <联系人名>  --db-dir <解密目录> [--output-dir ./output]
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="wechat-capture",
        description="微信聊天记录导出工具 — 截图模式 + 数据库模式",
    )
    subparsers = parser.add_subparsers(dest="mode", help="导出模式")

    # ── 截图模式 ──
    sp_ss = subparsers.add_parser(
        "screenshot",
        aliases=["ss"],
        help="截图模式：自动滚动微信窗口逐页截图（零侵入，无需解密）",
    )
    sp_ss.add_argument("contact", help="联系人名称（需先在微信中打开该聊天）")
    sp_ss.add_argument("--output-dir", "-o", default="./output", help="输出目录（默认 ./output）")
    sp_ss.add_argument("--max-scroll", type=int, default=150, help="向上滚动最大批次（默认 150）")

    # ── 数据库模式 ──
    sp_db = subparsers.add_parser(
        "database",
        aliases=["db"],
        help="数据库模式：从解密后的本地数据库读取（需先解密微信数据库）",
    )
    sp_db.add_argument("contact", help="联系人名称/备注名")
    sp_db.add_argument("--db-dir", "-d", required=True, help="解密后的数据目录路径")
    sp_db.add_argument("--output-dir", "-o", default="./output", help="输出目录（默认 ./output）")

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(0)

    if args.mode in ("screenshot", "ss"):
        from .screenshot import export
        export(
            contact_name=args.contact,
            output_dir=args.output_dir,
            max_scroll_batches=args.max_scroll,
        )

    elif args.mode in ("database", "db"):
        from .database import export
        export(
            contact_name=args.contact,
            decrypted_dir=args.db_dir,
            output_dir=args.output_dir,
        )


if __name__ == "__main__":
    main()
