import os
from datetime import datetime

import pytest

from toss_bin.trashinfo import (
    TrashInfo,
    TrashInfoError,
    decode_path,
    encode_path,
    format_info,
    parse_info,
)

WHEN = datetime(2026, 11, 3, 14, 5, 9)


def test_format_matches_spec_layout():
    text = format_info(TrashInfo("/home/me/notes old.txt", WHEN))
    assert text == (
        "[Trash Info]\n"
        "Path=/home/me/notes%20old.txt\n"
        "DeletionDate=2026-11-03T14:05:09\n"
    )


@pytest.mark.parametrize(
    "path",
    ["/tmp/plain", "/tmp/with space", "/tmp/café", "/tmp/100%", "/tmp/a#b?c"],
)
def test_round_trip(path):
    assert parse_info(format_info(TrashInfo(path, WHEN))) == TrashInfo(path, WHEN)


def test_non_utf8_name_round_trips():
    path = os.fsdecode(b"/tmp/bad\xff")
    assert encode_path(path) == "/tmp/bad%FF"
    assert decode_path("/tmp/bad%FF") == path


def test_parse_ignores_unknown_keys_and_other_groups():
    text = (
        "# comment\n"
        "[Trash Info]\n"
        "Path=/a\n"
        "X-Extra=1\n"
        "DeletionDate=2026-11-03T14:05:09\n"
        "[Other]\n"
        "Path=/b\n"
    )
    assert parse_info(text) == TrashInfo("/a", WHEN)


@pytest.mark.parametrize(
    "text",
    [
        "Path=/a\nDeletionDate=2026-11-03T14:05:09\n",
        "[Trash Info]\nDeletionDate=2026-11-03T14:05:09\n",
        "[Trash Info]\nPath=/a\n",
        "[Trash Info]\nPath=/a\nDeletionDate=yesterday\n",
    ],
)
def test_parse_rejects_broken_files(text):
    with pytest.raises(TrashInfoError):
        parse_info(text)
