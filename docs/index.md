# window-snap

window-snap is a Windows command-line tool that moves and resizes desktop windows based on a YAML configuration file.

It is useful if you regularly want the same app layout on startup, after docking/undocking, or when switching monitor setups.

## What This Project Does

- Applies a YAML-defined layout to top-level windows.
- Matches windows by title, or by executable name.
- Supports multi-monitor placement using a 1-based monitor index.
- Accepts both absolute pixel values and fractional values for placement and size.
- Supports maximized window targets.
- Supports putting the window currently on top with `on_top: true`.

  Note: The next window to process may compete with this, so put these late in the config if desired.

- Can capture current window positions into a starter config.

## Quick Start

1. Install the tool.
2. Generate a starter config from your current layout.
3. Edit the config as needed.
4. Run window-snap whenever you want to apply the layout.


## Documentation

| Page | Description |
| --- | --- |
| [Installation](installation.md) | Setup and installation instructions. |
| [Usage](usage.md) | Command reference and configuration examples. |
| [Changelog](changelog.md) | Project release history in Keep a Changelog format. |

## Requirements

- Windows OS
- Python 3.11+

## Project Links

- Source repository: <https://github.com/mshafer1/window-snap>
- Package name: `window_snap`
