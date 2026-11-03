import os

import pytest

from toss_bin.trash import TossError, put


def test_refuses_root(trash):
    with pytest.raises(TossError, match="refusing to trash /"):
        put("/")


def test_refuses_home(trash, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "work"))
    with pytest.raises(TossError, match="home folder"):
        put("~")
    with pytest.raises(TossError, match="home folder"):
        put(str(tmp_path / "work") + "/")


@pytest.mark.parametrize("arg", [".", "..", "sub/.", "sub/../"])
def test_refuses_dot_and_dotdot(trash, tmp_path, arg):
    (tmp_path / "work" / "sub").mkdir()
    with pytest.raises(TossError, match='"." or ".."'):
        put(arg)
    assert (tmp_path / "work" / "sub").is_dir()


def test_refuses_items_already_in_trash(trash, tmp_path):
    (tmp_path / "work" / "a").write_text("x")
    entry = put("a")
    with pytest.raises(TossError, match="already in the trash"):
        put(str(entry.file_path))
    with pytest.raises(TossError, match="already in the trash"):
        put(str(trash))


def test_refuses_folder_that_contains_the_trash(trash, tmp_path):
    (tmp_path / "work" / "a").write_text("x")
    put("a")
    with pytest.raises(TossError, match="contains the trash"):
        put(str(tmp_path / "data"))
    assert trash.is_dir()


def test_similar_prefix_is_not_inside(trash, tmp_path):
    # /…/data/Trash2 is not inside /…/data/Trash
    other = tmp_path / "data" / "Trash2"
    other.mkdir(parents=True)
    put(str(other))
    assert not other.exists()
    assert os.path.isdir(trash / "files" / "Trash2")
