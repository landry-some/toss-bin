"""The home trash: moving items in, and finding what is there."""

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .trashinfo import TrashInfo, format_info

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
