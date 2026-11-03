# Roadmap

Rough plan after v0.1. Hours are estimates, about 29 hours in total.

## v0.1

- [ ] `toss FILE...` moves files and folders into the FreeDesktop trash
- [ ] `toss list [PATTERN]` shows what is in the trash
- [ ] `toss restore TARGET` puts an item back where it came from
- [ ] `toss empty` deletes for good, with `--older-than` and a confirmation prompt
- [ ] Refuse protected paths (`/`, home, the trash itself) with clear errors

## Features

- [ ] Per-volume trash (`$topdir/.Trash-$uid`) so files on USB drives and other
      mounts are not copied to the home trash (4h)
- [ ] `toss undo` to restore everything from the last `toss` call (2h)
- [ ] Interactive restore picker when a match is ambiguous (3h)
- [ ] `--older-than` and `--larger-than` filters for `toss list` (1.5h)
- [ ] `toss du` to show the total trash size and the biggest items (1h)
- [ ] macOS backend using `~/.Trash` (3h)

## Bugs and edge cases

- [ ] Paths that are not valid UTF-8, and percent-encoding round trips (1.5h)
- [ ] Broken symlinks and symlinks to folders: trash the link, never the target (1h)
- [ ] Keep the spec's `directorysizes` cache in sync when trashing and emptying (1.5h)
- [ ] Detect and clean orphan entries (info file without data, or the opposite) (1h)

## Refactors

- [ ] Split a small trash backend interface so per-volume and macOS trash fit in (2h)
- [ ] One path-resolution helper shared by put, restore and the safety checks (1h)

## Tests

- [ ] Cross-device move tests using a tmpfs mount (1.5h)
- [ ] Property tests for name escaping and unique names with hypothesis (1.5h)
- [ ] CI on Linux and macOS with GitHub Actions (1h)

## Docs

- [ ] Man page (1.5h)
- [ ] Guide for aliasing `rm` to `toss` safely in bash, zsh and fish (0.5h)
- [ ] CHANGELOG and a first tagged release (1h)
