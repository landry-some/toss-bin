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


@pytest.fixture(autouse=True)
def state_home(tmp_path, monkeypatch):
    """Keep the `toss undo` record out of the real ~/.local/state."""
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    return state
