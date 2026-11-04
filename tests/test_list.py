from datetime import datetime, timedelta

import pytest

from toss_bin.cli import human_size, main
from toss_bin.trash import entries, put


def test_entries_sorted_oldest_first(trash, tmp_path):
    work = tmp_path / "work"
    for name, day in [("b", 5), ("a", 3), ("c", 4)]:
        (work / name).write_text("x")
        put(name, now=datetime(2026, 11, day, 12, 0))
    assert [e.name for e in entries()] == ["a", "c", "b"]


def test_entries_skip_broken_and_orphan_info(trash, tmp_path):
    (tmp_path / "work" / "ok").write_text("x")
    put("ok")
    (trash / "info" / "junk.trashinfo").write_text("not an info file")
    (trash / "info" / "orphan.trashinfo").write_text(
        "[Trash Info]\nPath=/x/orphan\nDeletionDate=2026-11-03T10:00:00\n"
    )
    (trash / "info" / "README").write_text("ignored")
    assert [e.name for e in entries()] == ["ok"]


def test_entries_of_missing_trash(trash):
    assert entries() == []


def test_human_size():
    assert human_size(0) == "0B"
    assert human_size(1023) == "1023B"
    assert human_size(1536) == "1.5K"
    assert human_size(5 * 1024**3) == "5.0G"


def test_list_output(trash, tmp_path, capsys):
    work = tmp_path / "work"
    (work / "notes.txt").write_text("a" * 2048)
    (work / "dir").mkdir()
    (work / "dir" / "f").write_text("abc")
    put("notes.txt", now=datetime(2026, 11, 3, 9, 30))
    put("dir", now=datetime(2026, 11, 3, 10, 0))

    assert main(["list"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [
        f"2026-11-03 09:30     2.0K  notes.txt  {work}/notes.txt",
        f"2026-11-03 10:00       3B  dir  {work}/dir",
    ]


def test_list_filters(trash, tmp_path, capsys):
    work = tmp_path / "work"
    for name in ["report.pdf", "photo.jpg", "notes.txt"]:
        (work / name).write_text("x")
        put(name)

    main(["list", "*.pdf"])
    assert [line.split()[-2] for line in capsys.readouterr().out.splitlines()] == ["report.pdf"]
    main(["ls", "photo"])
    assert [line.split()[-2] for line in capsys.readouterr().out.splitlines()] == ["photo.jpg"]


def test_list_empty_trash(trash, capsys):
    assert main(["list"]) == 0
    assert "trash is empty" in capsys.readouterr().err


def test_parse_size():
    from toss_bin.trash import parse_size

    assert parse_size("500") == 500
    assert parse_size("100b") == 100
    assert parse_size("2K") == 2048
    assert parse_size("1.5m") == 1536 * 1024
    assert parse_size("1G") == 1024**3


@pytest.mark.parametrize("text", ["", "K", "-1K", "1.2.3M", "10X", "ten"])
def test_parse_size_rejects(text):
    from toss_bin.trash import TossError, parse_size

    with pytest.raises(TossError, match="bad size"):
        parse_size(text)


def test_list_older_than(trash, tmp_path, capsys):
    work = tmp_path / "work"
    now = datetime.now()
    for name, age in [("old", 40), ("new", 2)]:
        (work / name).write_text("x")
        put(name, now=now - timedelta(days=age))
    assert main(["list", "--older-than", "30d"]) == 0
    assert [line.split()[-2] for line in capsys.readouterr().out.splitlines()] == ["old"]


def test_list_larger_than(trash, tmp_path, capsys):
    work = tmp_path / "work"
    (work / "big").write_text("x" * 4096)
    (work / "small").write_text("x" * 100)
    (work / "edge").write_text("x" * 1024)
    for name in ["big", "small", "edge"]:
        put(name)
    assert main(["list", "--larger-than", "1K"]) == 0
    assert [line.split()[-2] for line in capsys.readouterr().out.splitlines()] == ["big"]


def test_list_filters_combine(trash, tmp_path, capsys):
    work = tmp_path / "work"
    now = datetime.now()
    for name, age, size in [("a.log", 40, 5000), ("b.log", 2, 5000), ("c.txt", 40, 5000), ("d.log", 40, 10)]:
        (work / name).write_text("x" * size)
        put(name, now=now - timedelta(days=age))
    assert main(["list", "*.log", "--older-than", "1w", "--larger-than", "1K"]) == 0
    assert [line.split()[-2] for line in capsys.readouterr().out.splitlines()] == ["a.log"]


def test_list_bad_filters(trash, capsys):
    assert main(["list", "--older-than", "soon"]) == 2
    assert "bad age" in capsys.readouterr().err
    assert main(["list", "--larger-than", "huge"]) == 2
    assert "bad size" in capsys.readouterr().err
