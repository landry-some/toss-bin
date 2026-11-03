"""Command-line entry point for `toss`."""

import argparse
import sys

from . import __version__
from .trash import TossError, disk_size, entries, matches, put


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


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024 or unit == "T":
            return f"{n}B" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    raise AssertionError("unreachable")


def cmd_list(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="toss list", description="Show what is in the trash.")
    p.add_argument("pattern", nargs="?", help="glob or text to match against the original path")
    args = p.parse_args(argv)

    items = entries()
    if not items:
        print("trash is empty", file=sys.stderr)
        return 0
    if args.pattern:
        items = [e for e in items if matches(e, args.pattern)]
    for e in items:
        try:
            size = human_size(disk_size(e.file_path))
        except OSError:
            size = "?"
        print(f"{e.deleted:%Y-%m-%d %H:%M}  {size:>7}  {e.name}  {e.original}")
    return 0


COMMANDS = {"put": cmd_put, "list": cmd_list, "ls": cmd_list}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # A file literally named "list" can still be tossed with `toss ./list` or `toss put list`.
    if argv and argv[0] in COMMANDS:
        return COMMANDS[argv[0]](argv[1:])
    return cmd_put(argv)


if __name__ == "__main__":
    sys.exit(main())
