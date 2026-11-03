import pytest


@pytest.fixture
def trash(tmp_path, monkeypatch):
    """Point XDG_DATA_HOME at a temp folder and work from a temp cwd."""
    data = tmp_path / "data"
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.chdir(work)
    return data / "Trash"
