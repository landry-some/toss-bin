from datetime import datetime

import pytest

from toss_bin.cli import main
from toss_bin.trash import TossError, entries, find, put, restore


def toss(work, name, text="x", **kw):
    (work / name).write_text(text)
    return put(name, **kw)


def test_restore_to_original_place(trash, tmp_path):
    work = tmp_path / "work"
    entry = toss(work, "notes.txt", "hello")
    assert restore(entry) == str(work / "notes.txt")
    assert (work / "notes.txt").read_text() == "hello"
    assert entries() == []
    assert list((trash / "info").iterdir()) == []


def test_restore_recreates_missing_parent(trash, tmp_path):
    work = tmp_path / "work"
    (work / "proj").mkdir()
    (work / "proj" / "main.c").write_text("int main;")
    entry = put("proj/main.c")
    (work / "proj").rmdir()
    restore(entry)
    assert (work / "proj" / "main.c").read_text() == "int main;"


def test_restore_never_overwrites(trash, tmp_path):
    work = tmp_path / "work"
    entry = toss(work, "a", "old")
    (work / "a").write_text("new")
    with pytest.raises(TossError, match="already exists"):
        restore(entry)
    assert (work / "a").read_text() == "new"
    assert entries() == [entry]


def test_restore_into_other_folder(trash, tmp_path):
    work = tmp_path / "work"
    entry = toss(work, "a", "old")
    (work / "a").write_text("new")
    (work / "elsewhere").mkdir()
    restore(entry, to="elsewhere")
    assert (work / "elsewhere" / "a").read_text() == "old"
    with pytest.raises(TossError, match="not a folder"):
        restore(toss(work, "b"), to="nope")


def test_find_by_id_path_and_name(trash, tmp_path):
    work = tmp_path / "work"
    (work / "sub").mkdir()
    a = toss(work, "a.txt")
    b = toss(work, "sub/b.txt")
    items = entries()
    assert find("a.txt", items) == a
    assert find(str(work / "sub" / "b.txt"), items) == b
    assert find("sub/b.txt", items) == b
    assert find("b.txt", items) == b
    with pytest.raises(TossError, match="not in the trash"):
        find("zzz", items)


def test_ambiguous_name_lists_ids(trash, tmp_path):
    work = tmp_path / "work"
    toss(work, "a.txt", now=datetime(2026, 11, 1, 8, 0))
    toss(work, "a.txt", now=datetime(2026, 11, 2, 8, 0))
    items = entries()
    with pytest.raises(TossError) as err:
        find(str(work / "a.txt"), items)
    assert "matches 2 items" in str(err.value)
    assert "a.2.txt  (2026-11-02 08:00" in str(err.value)
    # the bare name is ambiguous too, even though it's also the first item's ID
    with pytest.raises(TossError, match="matches 2 items"):
        find("a.txt", items)
    # --id picks exactly one, and an unused ID works without it
    assert find("a.txt", items, by_id=True).deleted == datetime(2026, 11, 1, 8, 0)
    assert find("a.2.txt", items).deleted == datetime(2026, 11, 2, 8, 0)
    with pytest.raises(TossError, match="no trash item"):
        find("a.3.txt", items, by_id=True)


def test_cli_restore(trash, tmp_path, capsys):
    work = tmp_path / "work"
    toss(work, "a")
    toss(work, "b")
    assert main(["restore", "a", "ghost", "b"]) == 1
    captured = capsys.readouterr()
    assert f"restored {work}/a" in captured.out
    assert f"restored {work}/b" in captured.out
    assert "toss: ghost: not in the trash" in captured.err
    assert (work / "a").exists() and (work / "b").exists()


def test_cli_restore_by_id(trash, tmp_path):
    work = tmp_path / "work"
    toss(work, "a", "first")
    toss(work, "a", "second")
    assert main(["restore", "a"]) == 1
    assert main(["restore", "--id", "a.2"]) == 0
    assert (work / "a").read_text() == "second"
