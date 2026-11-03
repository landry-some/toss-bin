"""Command-line entry point for `toss`."""

import argparse
import sys

from . import __version__
from .trash import TossError, put


def _put_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="toss",
        description="Move files and folders to the trash instead of deleting them.",
    )
    p.add_argument("paths", nargs="+", metavar="FILE")
    p.add_argument("-f", "--force", action="store_true", help="ignore missing files")
    p.add_argument("-v", "--verbose", action="store_true", help="print each trashed item")
    # rm habits: -r/-i/-d are accepted and do nothing, folders are always moved whole.
    p.add_argument("-r", "-R", "--recursive", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--version", action="version", version=f"toss {__version__}")
    return p


def cmd_put(argv: list[str]) -> int:
    args = _put_parser().parse_args(argv)
    status = 0
    for path in args.paths:
        try:
            entry = put(path)
        except TossError as e:
            if args.force and "no such file" in str(e):
                continue
            print(f"toss: {e}", file=sys.stderr)
            status = 1
            continue
        if args.verbose:
            print(f"{entry.original} -> trash ({entry.name})")
    return status


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "put":
        argv = argv[1:]
    return cmd_put(argv)


if __name__ == "__main__":
    sys.exit(main())
