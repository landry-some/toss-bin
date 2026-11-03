"""The home trash: moving items in, and finding what is there."""

import fnmatch
import os
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .trashinfo import TrashInfo, TrashInfoError, format_info, parse_info

INFO_SUFFIX = ".trashinfo"


class TossError(Exception):
    """A user-facing failure; the message is printed as is."""


def home_trash() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(data_home) / "Trash"


@dataclass(frozen=True)
class Entry:
    """One trashed item. `name` is its file name inside Trash/files and its ID."""

    trash: Path
    name: str
    original: str
    deleted: datetime

    @property
    def file_path(self) -> Path:
        return self.trash / "files" / self.name

    @property
    def info_path(self) -> Path:
        return self.trash / "info" / (self.name + INFO_SUFFIX)


def absolute(path: str) -> str:
    """Make `path` absolute without following a symlink at the end."""
    return os.path.normpath(os.path.join(os.getcwd(), os.path.expanduser(path)))


def _candidates(base: str):
    """`notes.txt`, `notes.2.txt`, `notes.3.txt`, ... (dotfiles keep their dot)."""
    yield base
    stem, ext = os.path.splitext(base)
    n = 2
    while True:
        yield f"{stem}.{n}{ext}"
        n += 1


def _reserve_info(trash: Path, base: str, text: str) -> str:
    """Create the info file under a free name and return that name.

    O_EXCL makes the reservation atomic, so two `toss` runs at once never pick
    the same name. A name is free only if there's no data file under it either.
    """
    info_dir = trash / "info"
    files_dir = trash / "files"
    for name in _candidates(base):
        if os.path.lexists(files_dir / name):
            continue
        try:
            fd = os.open(info_dir / (name + INFO_SUFFIX), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        return name
    raise AssertionError("unreachable")


def _is_within(path: str, parent: str) -> bool:
    return path == parent or path.startswith(parent.rstrip(os.sep) + os.sep)


def check_safe(path: str, original: str, trash: Path) -> None:
    """Refuse paths that `rm` users almost never mean, or that would break the trash."""
    if os.path.basename(path.rstrip(os.sep)) in (".", ".."):
        raise TossError(f'{path}: refusing to trash "." or ".."')
    if original == os.sep:
        raise TossError(f"{path}: refusing to trash /")
    if original == absolute("~"):
        raise TossError(f"{path}: refusing to trash your home folder")
    trash_dir = absolute(str(trash))
    if _is_within(original, trash_dir):
        raise TossError(f"{path}: already in the trash, use 'toss empty' to delete it")
    if _is_within(trash_dir, original):
        raise TossError(f"{path}: contains the trash folder ({trash_dir})")


def put(path: str, trash: Path | None = None, now: datetime | None = None) -> Entry:
    """Move `path` into the trash and return the new entry."""
    trash = trash or home_trash()
    original = absolute(path)
    check_safe(path, original, trash)
    if not os.path.lexists(original):
        raise TossError(f"{path}: no such file or directory")

    (trash / "files").mkdir(parents=True, exist_ok=True, mode=0o700)
    (trash / "info").mkdir(parents=True, exist_ok=True, mode=0o700)

    deleted = (now or datetime.now()).replace(microsecond=0)
    text = format_info(TrashInfo(original, deleted))
    name = _reserve_info(trash, os.path.basename(original), text)
    entry = Entry(trash, name, original, deleted)
    try:
        # rename() when on the same filesystem, copy + delete otherwise.
        # Symlinks are moved as links, never followed.
        shutil.move(original, entry.file_path)
    except OSError as e:
        entry.info_path.unlink(missing_ok=True)
        raise TossError(f"{path}: {e.strerror or e}") from None
    return entry


def entries(trash: Path | None = None) -> list[Entry]:
    """Every readable entry in the trash, oldest first.

    Info files that can't be parsed, or whose data file is gone, are skipped.
    """
    trash = trash or home_trash()
    info_dir = trash / "info"
    if not info_dir.is_dir():
        return []
    found = []
    for info_file in info_dir.iterdir():
        if not info_file.name.endswith(INFO_SUFFIX):
            continue
        name = info_file.name[: -len(INFO_SUFFIX)]
        try:
            info = parse_info(info_file.read_text(encoding="utf-8", errors="surrogateescape"))
        except (OSError, TrashInfoError):
            continue
        entry = Entry(trash, name, info.path, info.deleted)
        if os.path.lexists(entry.file_path):
            found.append(entry)
    found.sort(key=lambda e: (e.deleted, e.name))
    return found


def disk_size(path: Path) -> int:
    """Bytes used by a file or a whole folder; symlinks count as themselves."""
    st = os.lstat(path)
    if not stat.S_ISDIR(st.st_mode):
        return st.st_size
    total = 0
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def matches(entry: Entry, pattern: str) -> bool:
    """Glob against the original name or path; plain text matches any part of the path."""
    if any(c in pattern for c in "*?["):
        return fnmatch.fnmatchcase(os.path.basename(entry.original), pattern) or fnmatch.fnmatchcase(
            entry.original, pattern
        )
    return pattern in entry.original or pattern == entry.name


def find(target: str, items: list[Entry], by_id: bool = False) -> Entry:
    """Pick one entry by original path, then original name, then trash ID.

    With `by_id`, only the trash ID is used. That's the way to choose between
    several items that were deleted from the same path.
    """
    ids = [e for e in items if e.name == target]
    if by_id:
        if not ids:
            raise TossError(f"{target}: no trash item with this ID")
        return ids[0]
    wanted = absolute(target)
    found = [e for e in items if e.original == wanted]
    if not found:
        found = [e for e in items if os.path.basename(e.original) == target]
    if not found:
        found = ids
    if not found:
        raise TossError(f"{target}: not in the trash")
    if len(found) > 1:
        lines = "\n".join(f"  {e.name}  ({e.deleted:%Y-%m-%d %H:%M}, {e.original})" for e in found)
        raise TossError(
            f"{target}: matches {len(found)} items, pick one with 'toss restore --id ID':\n{lines}"
        )
    return found[0]


def restore(entry: Entry, to: str | None = None) -> str:
    """Move `entry` back to where it came from, or into folder `to`. Returns the new path."""
    if to is not None:
        if not os.path.isdir(to):
            raise TossError(f"{to}: not a folder")
        dest = os.path.join(absolute(to), os.path.basename(entry.original))
    else:
        dest = entry.original
    if os.path.lexists(dest):
        raise TossError(f"{dest}: already exists, not overwriting (use --to DIR)")
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(entry.file_path, dest)
    except OSError as e:
        raise TossError(f"{dest}: {e.strerror or e}") from None
    entry.info_path.unlink(missing_ok=True)
    return dest
