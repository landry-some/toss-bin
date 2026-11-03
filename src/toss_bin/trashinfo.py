"""Read and write `.trashinfo` files as described by the FreeDesktop Trash spec.

A trashinfo file looks like this:

    [Trash Info]
    Path=/home/me/notes%20old.txt
    DeletionDate=2026-11-03T14:05:09

Path is absolute and percent-encoded byte by byte, so names that are not valid
UTF-8 survive the round trip. DeletionDate is local time without a timezone.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote_from_bytes, unquote_to_bytes

HEADER = "[Trash Info]"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class TrashInfoError(ValueError):
    """Raised when a trashinfo file can't be parsed."""


@dataclass(frozen=True)
class TrashInfo:
    path: str
    deleted: datetime


def encode_path(path: str) -> str:
    return quote_from_bytes(os.fsencode(path), safe="/")


def decode_path(value: str) -> str:
    return os.fsdecode(unquote_to_bytes(value))


def format_info(info: TrashInfo) -> str:
    return (
        f"{HEADER}\n"
        f"Path={encode_path(info.path)}\n"
        f"DeletionDate={info.deleted.strftime(DATE_FORMAT)}\n"
    )


def parse_info(text: str) -> TrashInfo:
    lines = [line.strip() for line in text.splitlines()]
    try:
        start = lines.index(HEADER)
    except ValueError:
        raise TrashInfoError("missing [Trash Info] header") from None

    fields = {}
    for line in lines[start + 1 :]:
        if line.startswith("["):
            break  # another group starts; the spec only defines this one
        key, sep, value = line.partition("=")
        if sep and key not in fields:
            fields[key] = value

    if "Path" not in fields:
        raise TrashInfoError("missing Path")
    try:
        deleted = datetime.strptime(fields.get("DeletionDate", ""), DATE_FORMAT)
    except ValueError:
        raise TrashInfoError("missing or bad DeletionDate") from None
    return TrashInfo(path=decode_path(fields["Path"]), deleted=deleted)
