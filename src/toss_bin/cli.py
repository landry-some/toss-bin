"""Command-line entry point for `toss`."""

import argparse
import sys
from datetime import datetime

from . import __version__
from .trash import (
    TossError,
    disk_size,
    entries,
    find,
    matches,
    parse_age,
    purge,
    put,
    restore,
)


def _put_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="toss",
        description="Move files and folders to the trash instead of deleting them.",
        epilog="other commands:\n"
        "  toss list [PATTERN]            show what is in the trash\n"
        "  toss restore TARGET...         put items back where they were\n"
        "  toss empty [--older-than AGE]  delete trashed items for good\n"
        "run 'toss COMMAND --help' for details.\n"
        "To trash a file named like a "
        "command, use 'toss ./list'.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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


def _size(path) -> int:
    try:
        return disk_size(path)
    except OSError:
        return 0


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


def cmd_restore(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="toss restore",
        description="Put items back where they were. TARGET is the original path, the original "
        "file name, or a trash ID from 'toss list'.",
    )
    p.add_argument("targets", nargs="+", metavar="TARGET")
    p.add_argument("--to", metavar="DIR", help="restore into DIR instead of the original folder")
    p.add_argument("--id", action="store_true", help="treat each TARGET as a trash ID only")
    args = p.parse_args(argv)

    status = 0
    for target in args.targets:
        try:
            # Re-read each time so two targets can't resolve to the same entry.
            dest = restore(find(target, entries(), by_id=args.id), to=args.to)
        except TossError as e:
            print(f"toss: {e}", file=sys.stderr)
            status = 1
            continue
        print(f"restored {dest}")
    return status


def cmd_empty(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="toss empty", description="Delete trashed items for good.")
    p.add_argument("--older-than", metavar="AGE", help="only items deleted more than AGE ago (30d, 12h, 2w)")
    p.add_argument("-y", "--yes", action="store_true", help="don't ask for confirmation")
    args = p.parse_args(argv)

    items = entries()
    if args.older_than:
        try:
            cutoff = datetime.now() - parse_age(args.older_than)
        except TossError as e:
            print(f"toss: {e}", file=sys.stderr)
            return 2
        items = [e for e in items if e.deleted < cutoff]
    if not items:
        print("nothing to delete", file=sys.stderr)
        return 0

    total = human_size(sum(_size(e.file_path) for e in items))
    if not args.yes:
        if not sys.stdin.isatty():
            print("toss: not a terminal, pass --yes to empty the trash", file=sys.stderr)
            return 1
        answer = input(f"Permanently delete {len(items)} item(s), {total}? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("cancelled", file=sys.stderr)
            return 1

    status = 0
    for e in items:
        try:
            purge(e)
        except TossError as err:
            print(f"toss: {err}", file=sys.stderr)
            status = 1
    print(f"deleted {len(items)} item(s), {total}")
    return status


COMMANDS = {
    "put": cmd_put,
    "list": cmd_list,
    "ls": cmd_list,
    "restore": cmd_restore,
    "empty": cmd_empty,
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # A file literally named "list" can still be tossed with `toss ./list` or `toss put list`.
    if argv and argv[0] in COMMANDS:
        return COMMANDS[argv[0]](argv[1:])
    return cmd_put(argv)


if __name__ == "__main__":
    sys.exit(main())
