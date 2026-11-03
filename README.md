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

## Run

```bash
toss notes.txt build/            # move a file and a folder to the trash
toss -f maybe-missing.log        # -f: no error if it doesn't exist
toss -v *.tmp                    # -v: print each item and its trash ID
toss list                        # everything in the trash, oldest first
toss list '*.pdf'                # glob on the original name or path
toss list projects/old           # or any part of the original path
toss restore notes.txt           # back to where it was
toss restore --to ~/tmp notes.txt
toss restore --id notes.2.txt    # pick one when several share a path
toss empty --older-than 30d      # delete for good, asks first
toss empty -y                    # empty everything without asking
```

`toss` also accepts `-r`, `-R` and `-rf` so `rm` habits keep working. Folders are
always moved whole, so `-r` does nothing. `toss put FILE` is the long form; use it,
or `toss ./list`, to trash a file that is named like a command.

### Listing

```
2026-11-03 09:30     2.0K  notes.txt    /home/me/notes.txt
2026-11-03 10:00     2.0K  notes.2.txt  /home/me/notes.txt
2026-11-03 10:02   184.0K  build        /home/me/proj/build
```

The columns are the deletion time, the size on disk, the trash ID and the original
path. The trash ID is the item's name inside `Trash/files/`. When a name is already
taken, a number is added before the extension (`notes.2.txt`).

### Restoring

`TARGET` is matched against the original path first, then the original file name,
and only then the trash ID. If it matches more than one item, `toss` lists them and
restores nothing. Run it again with `--id`.

A restore never overwrites anything. If the original path is taken, `toss` stops;
use `--to DIR` to put the item somewhere else. If the original folder is gone, it is
created again.

### Emptying

`toss empty` asks before deleting anything and refuses to run without a terminal
unless you pass `--yes`. `--older-than` takes a number with `m`, `h`, `d` or `w`
(minutes, hours, days, weeks).

### What it won't trash

`/`, your home folder, `.` and `..`, anything already in the trash, and any folder
that contains the trash (such as `~/.local`). Symlinks are moved as links, and their
targets are never touched.

## Where the trash lives

`$XDG_DATA_HOME/Trash`, which is `~/.local/share/Trash` by default. Each item is a
file or folder in `Trash/files/` plus a `Trash/info/<name>.trashinfo` file with the
original path and the deletion time, as the
[FreeDesktop Trash spec](https://specifications.freedesktop.org/trash-spec/latest/)
describes. Files from other filesystems (USB drives, `/tmp` on tmpfs) are copied into
the home trash and then removed. Per-volume trash folders are on the
[roadmap](ROADMAP.md).

Linux only for now. It should work on other Unix systems that use the same layout,
but it has only been tested on Linux.

## Test

```bash
python -m pytest
```

Tests point `XDG_DATA_HOME` at a temporary folder, so they never touch your real
trash.
