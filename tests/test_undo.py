import os

from toss_bin.cli import main
from toss_bin.trash import entries, load_last_call, put


def test_undo_restores_the_whole_last_call(trash, tmp_path, capsys):
    work = tmp_path / "work"
    for name in ["a", "b", "c"]:
        (work / name).write_text(name)
    assert main(["a"]) == 0
    assert main(["b", "c"]) == 0

    assert main(["undo"]) == 0
    assert sorted(p.name for p in work.iterdir()) == ["b", "c"]
    assert [e.name for e in entries()] == ["a"]
    assert capsys.readouterr().out.splitlines() == [f"restored {work}/b", f"restored {work}/c"]
    assert load_last_call() == []


def test_undo_twice_has_nothing_to_undo(trash, tmp_path, capsys):
    (tmp_path / "work" / "a").write_text("x")
    main(["a"])
    assert main(["undo"]) == 0
    assert main(["undo"]) == 1
    assert "nothing to undo" in capsys.readouterr().err


def test_undo_with_no_history(trash, capsys):
    assert main(["undo"]) == 1
    assert "nothing to undo" in capsys.readouterr().err


def test_failed_toss_keeps_previous_undo(trash, tmp_path):
    (tmp_path / "work" / "a").write_text("x")
    main(["a"])
    assert main(["missing"]) == 1
    assert main(["-f", "missing"]) == 0
    assert load_last_call() == ["a"]


def test_undo_uses_trash_ids_not_names(trash, tmp_path):
    work = tmp_path / "work"
    (work / "notes.txt").write_text("old")
    put("notes.txt")  # an older item with the same original path
    (work / "notes.txt").write_text("new")
    main(["notes.txt"])
    assert main(["undo"]) == 0
    assert (work / "notes.txt").read_text() == "new"
    assert [e.name for e in entries()] == ["notes.txt"]


def test_undo_skips_items_already_gone(trash, tmp_path, capsys):
    work = tmp_path / "work"
    (work / "a").write_text("a")
    (work / "b").write_text("b")
    main(["a", "b"])
    main(["restore", "a"])
    capsys.readouterr()
    assert main(["undo"]) == 1
    assert (work / "b").exists()
    assert "a: no trash item" in capsys.readouterr().err
    assert load_last_call() == []


def test_undo_keeps_blocked_items_for_retry(trash, tmp_path, capsys):
    work = tmp_path / "work"
    (work / "a").write_text("a")
    (work / "b").write_text("b")
    main(["a", "b"])
    (work / "a").write_text("in the way")
    assert main(["undo"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert (work / "b").read_text() == "b"
    assert load_last_call() == ["a"]

    os.remove(work / "a")
    assert main(["undo"]) == 0
    assert (work / "a").read_text() == "a"


def test_undo_record_survives_non_utf8_names(trash, tmp_path):
    name = os.fsdecode(b"caf\xe9")
    (tmp_path / "work" / name).write_text("x")
    main([name])
    assert load_last_call() == [name]
    assert main(["undo"]) == 0
    assert os.path.exists(tmp_path / "work" / name)
