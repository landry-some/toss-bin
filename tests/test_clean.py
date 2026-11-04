import io
import os

from toss_bin.cli import main
from toss_bin.trash import entries, orphans, put

INFO = "[Trash Info]\nPath=/x/{}\nDeletionDate=2026-11-03T10:00:00\n"


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


def make_orphans(trash, work):
    (work / "ok").write_text("x")
    put("ok")
    (trash / "info" / "gone.trashinfo").write_text(INFO.format("gone"))
    (trash / "files" / "stray").write_text("x")
    (trash / "files" / "straydir").mkdir()
    (trash / "files" / "straydir" / "f").write_text("x")
    (trash / "info" / "README").write_text("not a trashinfo, left alone")


def test_orphans_finds_both_kinds(trash, tmp_path):
    make_orphans(trash, tmp_path / "work")
    assert orphans() == [
        trash / "files" / "stray",
        trash / "files" / "straydir",
        trash / "info" / "gone.trashinfo",
    ]


def test_orphans_of_missing_trash(trash):
    assert orphans() == []


def test_orphan_symlink_data_is_found_and_target_kept(trash, tmp_path):
    work = tmp_path / "work"
    (work / "ok").write_text("x")
    put("ok")
    (work / "target").mkdir()
    (work / "target" / "keep").write_text("keep")
    os.symlink(work / "target", trash / "files" / "link")
    assert orphans() == [trash / "files" / "link"]
    assert main(["clean", "-y"]) == 0
    assert not os.path.lexists(trash / "files" / "link")
    assert (work / "target" / "keep").read_text() == "keep"


def test_clean_with_yes(trash, tmp_path, capsys):
    make_orphans(trash, tmp_path / "work")
    assert main(["clean", "--yes"]) == 0
    out = capsys.readouterr().out
    assert f"info without data: {trash}/info/gone.trashinfo" in out
    assert f"data without info: {trash}/files/stray" in out
    assert "deleted 3 orphan(s)" in out
    assert orphans() == []
    assert [e.name for e in entries()] == ["ok"]
    assert (trash / "info" / "README").exists()


def test_clean_refuses_without_terminal(trash, tmp_path, monkeypatch, capsys):
    make_orphans(trash, tmp_path / "work")
    monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))
    assert main(["clean"]) == 1
    assert "pass --yes" in capsys.readouterr().err
    assert len(orphans()) == 3


def test_clean_asks_first(trash, tmp_path, monkeypatch, capsys):
    make_orphans(trash, tmp_path / "work")
    monkeypatch.setattr("sys.stdin", FakeTTY("n\n"))
    assert main(["clean"]) == 1
    assert "Permanently delete 3 orphan(s)?" in capsys.readouterr().out
    assert len(orphans()) == 3
    monkeypatch.setattr("sys.stdin", FakeTTY("y\n"))
    assert main(["clean"]) == 0
    assert orphans() == []


def test_clean_nothing_to_do(trash, tmp_path, capsys):
    (tmp_path / "work" / "ok").write_text("x")
    put("ok")
    assert main(["clean"]) == 0
    assert "no orphans" in capsys.readouterr().err
