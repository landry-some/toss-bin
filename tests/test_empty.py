import io
import os
from datetime import datetime, timedelta

import pytest

from toss_bin.cli import main
from toss_bin.trash import TossError, entries, parse_age, purge, put


def toss(work, name, **kw):
    (work / name).write_text("x" * 10)
    return put(name, **kw)


def test_purge_file_folder_and_symlink(trash, tmp_path):
    work = tmp_path / "work"
    (work / "dir" / "deep").mkdir(parents=True)
    (work / "dir" / "deep" / "f").write_text("x")
    (work / "target").mkdir()
    (work / "target" / "keep").write_text("keep")
    os.symlink("target", work / "link")
    for e in [toss(work, "f"), put("dir"), put("link")]:
        purge(e)
    assert entries() == []
    assert list((trash / "files").iterdir()) == []
    assert list((trash / "info").iterdir()) == []
    assert (work / "target" / "keep").read_text() == "keep"


@pytest.mark.parametrize(
    "text,expected",
    [("30d", timedelta(days=30)), ("12h", timedelta(hours=12)), ("2W", timedelta(weeks=2)), ("90m", timedelta(minutes=90))],
)
def test_parse_age(text, expected):
    assert parse_age(text) == expected


@pytest.mark.parametrize("text", ["", "d", "30", "-3d", "1.5d", "3y"])
def test_parse_age_rejects(text):
    with pytest.raises(TossError, match="bad age"):
        parse_age(text)


def test_empty_with_yes(trash, tmp_path, capsys):
    work = tmp_path / "work"
    toss(work, "a")
    toss(work, "b")
    assert main(["empty", "--yes"]) == 0
    assert entries() == []
    assert "deleted 2 item(s), 20B" in capsys.readouterr().out


def test_empty_older_than(trash, tmp_path):
    work = tmp_path / "work"
    now = datetime.now()
    toss(work, "old", now=now - timedelta(days=40))
    toss(work, "new", now=now - timedelta(days=2))
    assert main(["empty", "--older-than", "30d", "-y"]) == 0
    assert [e.name for e in entries()] == ["new"]


def test_empty_bad_age(trash, capsys):
    assert main(["empty", "--older-than", "soon", "-y"]) == 2
    assert "bad age" in capsys.readouterr().err


def test_empty_refuses_without_terminal(trash, tmp_path, monkeypatch, capsys):
    toss(tmp_path / "work", "a")
    monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))
    assert main(["empty"]) == 1
    assert "pass --yes" in capsys.readouterr().err
    assert len(entries()) == 1


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


@pytest.mark.parametrize("answer,deleted", [("y\n", True), ("yes\n", True), ("\n", False), ("n\n", False)])
def test_empty_asks_first(trash, tmp_path, monkeypatch, capsys, answer, deleted):
    toss(tmp_path / "work", "a")
    monkeypatch.setattr("sys.stdin", FakeTTY(answer))
    assert main(["empty"]) == (0 if deleted else 1)
    assert "Permanently delete 1 item(s), 10B?" in capsys.readouterr().out
    assert (entries() == []) == deleted


def test_empty_nothing_to_do(trash, capsys):
    assert main(["empty", "-y"]) == 0
    assert "nothing to delete" in capsys.readouterr().err
