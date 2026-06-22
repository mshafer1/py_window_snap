# Window-Snap

The idea is simple, if you run the program, the windows that you want are put where you want them.

Why?

Well, because I have a system that has a screen attached that I can't see (it's used for comuication), and the computer likes to put the windows that were opened at startup on that screen.

Yes, I can solve this by selecting each in the task bar of my main monitor (since I have it set to show all windows there) and hitting
Windows + {arrow key} to move the window the correct direction to get it on my window.

But:

[![xkcd: Is It Worth the Time?](https://imgs.xkcd.com/comics/is_it_worth_the_time_2x.png)](https://xkcd.com/1205/)

Says that I can spend up to 4 minutes writing this app and save time over 5 years!

And the annoyance factor is through the roof, so here I go.

## Configuring

By default, the program looks at `%userprofile%\.config\window-snap\config.yaml`.

The folder to look in for `config.yaml` is configurable with the `WINDOW_SNAP_CONFIG_DIR` environment variable.

## Current Feature Set

This module currently supports the following:

- YAML-driven window layout management using a `windows` mapping in `config.yaml`.
- Window matching by title (default) or executable name (`find_by_exe`).
- Moving windows to a target monitor (monitor index in config is 1-based).
  - Leftmost monitor is 1, numbered increasing moving to the right
  - absolute pixel values (integer [0,monitor-width]), or
  - fractional values (0-1] relative to monitor work area.
- Maximize handling via `maximized: true`.
- Partial updates where unspecified values keep the window's current position/size.
- Multi-monitor awareness with monitor detection from window geometry.
- Safe handling when windows are missing or configuration entries are invalid (logs and continues).

Command-line features:

- `window-snap` applies the configured layout from the default config path.
- `window-snap --store-current` captures current top-level window positions and writes:
  - `_config_version`
  - `windows` (captured destinations)
  - `available_exe_names` (title -> executable mapping)
- `-v/--verbose` increases logging verbosity.
