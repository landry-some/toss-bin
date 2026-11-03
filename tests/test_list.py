from datetime import datetime

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
