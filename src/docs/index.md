# window-snap

window-snap is a Windows command-line tool that moves and resizes desktop windows based on a YAML configuration file.

It is useful if you regularly want the same app layout on startup, after docking/undocking, or when switching monitor setups.

## What This Project Does

- Applies a YAML-defined layout to top-level windows.
- Matches windows by title, or by executable name.
- Supports multi-monitor placement using a 1-based monitor index.
- Accepts both absolute pixel values and fractional values for placement and size.
- Supports maximized window targets.
- Can capture current window positions into a starter config.

## Quick Start

1. Install the tool.
2. Generate a starter config from your current layout.
3. Edit the config as needed.
4. Run window-snap whenever you want to apply the layout.

See the full setup guide here: [Installation](installation.md)

See command and config examples here: [Usage](usage.md)

## Requirements

- Windows OS
- Python 3.11+

## Project Links

- Source repository: <https://github.com/mshafer1/window-snap>
- Package name: `window_snap`
