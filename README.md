# toss-bin

`toss` is a replacement for `rm` that moves files into the trash instead of deleting
them. You can list what you threw away, restore an item to where it came from, and
empty the trash when you are sure.

It uses the FreeDesktop trash layout (`~/.local/share/Trash`), the same one GNOME,
KDE and most Linux file managers use, so items tossed from the terminal show up in the
file manager's trash and the other way round.

It's for people who live in a terminal on Linux and have lost a file to `rm` at least
once.

Built with Python 3.11+ and the standard library only. Tests use pytest.

## Install

```bash
git clone https://github.com/landry-some/toss-bin.git
cd toss-bin
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
```

## Test

```bash
python -m pytest
```

## Status

Work in progress. See [ROADMAP.md](ROADMAP.md) for the plan.
