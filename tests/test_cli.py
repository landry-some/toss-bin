from toss_bin.cli import main


def test_toss_several_files(trash, tmp_path, capsys):
    work = tmp_path / "work"
    (work / "a").write_text("x")
    (work / "b").mkdir()
    assert main(["-v", "a", "b"]) == 0
    assert sorted(p.name for p in (trash / "files").iterdir()) == ["a", "b"]
    assert "a -> trash (a)" in capsys.readouterr().out


def test_missing_file_fails_but_others_go(trash, tmp_path, capsys):
    (tmp_path / "work" / "a").write_text("x")
    assert main(["ghost", "a"]) == 1
    assert "toss: ghost: no such file" in capsys.readouterr().err
    assert (trash / "files" / "a").exists()


def test_force_ignores_missing(trash, capsys):
    assert main(["-f", "ghost"]) == 0
    assert capsys.readouterr().err == ""


def test_put_subcommand_and_rm_flags(trash, tmp_path):
    (tmp_path / "work" / "dir").mkdir()
    assert main(["put", "-rf", "dir"]) == 0
    assert (trash / "files" / "dir").is_dir()


def test_help_lists_subcommands(capsys):
    import pytest

    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for cmd in ("toss list", "toss restore", "toss empty"):
        assert cmd in out


def test_dot_slash_trashes_file_named_like_command(trash, tmp_path):
    (tmp_path / "work" / "list").write_text("x")
    assert main(["./list"]) == 0
    assert (trash / "files" / "list").exists()
