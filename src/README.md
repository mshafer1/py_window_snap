# window-snap

Installation:

`pipx install window_snap`

## Repository Instructions

- When updating project documentation, update both the `docs/` folder and this `README.md` so GitHub Pages and repository docs stay in sync.


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
- Temporary on-top handling via `on_top: true`.
- Partial updates where unspecified values keep the window's current position/size.
- Multi-monitor awareness with monitor detection from window geometry.
- Safe handling when windows are missing or configuration entries are invalid (logs and continues).

Example config snippet:

```yaml
windows:
  chrome.exe:
    find_by_exe: true
    on_top: true
    monitor: 2
    left: 0
    top: 0
    width: 0.5
    height: 1
```

`on_top` only puts the window on top at the moment during processing.

Command-line features:

- `window-snap` applies the configured layout from the default config path.
- Snapping is skipped when running inside a Windows Remote Desktop session.

  `window-snap --force` applies the configured layout even during a Remote Desktop session.

- `window-snap --store-current` captures current top-level window positions and writes:
  - `_config_version`
  - `windows` (captured destinations)
  - `available_exe_names` (title -> executable mapping)
- `-v/--verbose` increases logging verbosity.
