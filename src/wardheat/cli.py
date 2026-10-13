"""Command line: ``wardheat datapack {status,download,build,zip}``, ``wardheat check`` and ``wardheat site``."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="wardheat", description="Ward-level urban heat toolkit (Bengaluru workshop)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    dp = sub.add_parser("datapack", help="manage the pre-built Bengaluru data pack")
    dsub = dp.add_subparsers(dest="action", required=True)
    dsub.add_parser("status", help="list which layers are present")
    d = dsub.add_parser("download", help="download the pre-built pack")
    d.add_argument("--url", default=None)
    d.add_argument("--force", action="store_true")
    b = dsub.add_parser("build", help="build the pack from the original sources")
    b.add_argument("--step", action="append", help="run only this step (repeatable)")
    b.add_argument("--force", action="store_true")
    z = dsub.add_parser("zip", help="zip the pack for publishing as a release asset")
    z.add_argument("--out", default="dist/wardheat-datapack.zip")

    sub.add_parser("check", help="check the environment and network access")
    st = sub.add_parser("site", help="build the static course website from the notebooks")
    st.add_argument("--out", default="site")
    st.add_argument("--repo-url", default=None, help="link to the notebooks repository, shown in the sidebar")
    st.add_argument("--only", action="append", help="build only this notebook or page (repeatable)")
    st.add_argument("--home-url", default=None, help="link back to the website the course lives on")

    args = ap.parse_args(argv)
    if args.cmd == "datapack":
        from . import datapack

        if args.action == "status":
            import pandas as pd

            with pd.option_context("display.max_rows", 100, "display.width", 160):
                print(datapack.status())
        elif args.action == "download":
            print(datapack.download(**({"url": args.url} if args.url else {}), force=args.force))
        elif args.action == "build":
            from . import build

            build.run(args.step, force=args.force)
        elif args.action == "zip":
            datapack.write_manifest()
            datapack.zip_pack(args.out)
    elif args.cmd == "check":
        from .setup_check import run_checks

        ok = run_checks(verbose=True)
        return 0 if ok else 1
    elif args.cmd == "site":
        from .site import build

        build(args.out, repo_url=args.repo_url, only=args.only, home_url=args.home_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
