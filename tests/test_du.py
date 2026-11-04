from toss_bin.cli import main
from toss_bin.trash import put


def toss(work, name, size):
    (work / name).write_text("x" * size)
    put(name)


def test_du_biggest_first_with_total(trash, tmp_path, capsys):
    work = tmp_path / "work"
    toss(work, "small", 10)
    toss(work, "big", 3072)
    (work / "dir").mkdir()
    (work / "dir" / "f").write_text("x" * 2048)
    put("dir")

    assert main(["du"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in out[:-1]] == ["big", "dir", "small"]
    assert out[0] == f"   3.0K  big  {work}/big"
    assert out[-1].split() == ["5.0K", "total,", "3", "item(s)"]


def test_du_top_limits_items_not_total(trash, tmp_path, capsys):
    work = tmp_path / "work"
    for i, size in enumerate([100, 300, 200]):
        toss(work, f"f{i}", size)
    assert main(["du", "-n", "1"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [f"   300B  f1  {work}/f1", "   600B  total, 3 item(s)"]


def test_du_empty_trash(trash, capsys):
    assert main(["du"]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "trash is empty" in captured.err
