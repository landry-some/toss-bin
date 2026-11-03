import os
from datetime import datetime

import pytest

from toss_bin.trash import TossError, put
from toss_bin.trashinfo import parse_info

WHEN = datetime(2026, 11, 3, 9, 30, 0)


def test_put_moves_file_and_writes_info(trash, tmp_path):
    f = tmp_path / "work" / "notes.txt"
    f.write_text("hello")

    entry = put("notes.txt", now=WHEN)

    assert not f.exists()
    assert (trash / "files" / "notes.txt").read_text() == "hello"
    info = parse_info((trash / "info" / "notes.txt.trashinfo").read_text())
    assert info.path == str(f)
    assert info.deleted == WHEN
    assert entry.name == "notes.txt"


def test_same_name_gets_numbered(trash, tmp_path):
    names = []
    for _ in range(3):
        (tmp_path / "work" / "notes.txt").write_text("x")
        names.append(put("notes.txt").name)
    assert names == ["notes.txt", "notes.2.txt", "notes.3.txt"]


def test_dotfile_and_folder_names(trash, tmp_path):
    work = tmp_path / "work"
    for _ in range(2):
        (work / ".bashrc").write_text("x")
        (work / "build").mkdir()
        (work / "build" / "out.o").write_text("x")
        last = [put(".bashrc").name, put("build").name]
    assert last == [".bashrc.2", "build.2"]
    assert (trash / "files" / "build.2" / "out.o").exists()


def test_symlink_is_trashed_not_its_target(trash, tmp_path):
    work = tmp_path / "work"
    (work / "real").write_text("keep me")
    os.symlink("real", work / "link")
    put("link")
    assert (work / "real").read_text() == "keep me"
    assert (trash / "files" / "link").is_symlink()


def test_broken_symlink_can_be_trashed(trash, tmp_path):
    os.symlink("nowhere", tmp_path / "work" / "dangling")
    put("dangling")
    assert (trash / "files" / "dangling").is_symlink()


def test_missing_file_raises(trash):
    with pytest.raises(TossError, match="no such file"):
        put("ghost")
    assert not (trash / "info").exists() or not any((trash / "info").iterdir())


def test_failed_move_removes_reserved_info(trash, tmp_path, monkeypatch):
    (tmp_path / "work" / "a").write_text("x")

    def boom(*args):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr("toss_bin.trash.shutil.move", boom)
    with pytest.raises(TossError, match="Permission denied"):
        put("a")
    assert list((trash / "info").iterdir()) == []
