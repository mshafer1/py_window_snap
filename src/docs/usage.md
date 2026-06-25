# Usage

## Basic Command

Run without arguments to apply your configured layout:

```powershell
window-snap
```

## Generate a Starter Config

Capture current top-level windows and write `config.yaml`:

```powershell
window-snap --store-current
```

This writes a config file that includes:

- `_config_version`
- `windows`
- `available_exe_names`

## Remote Desktop Behavior

By default, snapping is skipped in Windows Remote Desktop sessions.

To force snapping anyway:

```powershell
window-snap --force
```

## Verbose Logging

Increase log verbosity with `-v`.

```powershell
window-snap -v
window-snap -vv
```

## Config Format

The main structure is a `windows` mapping.

Example:

```yaml
_config_version: 0.1.0
windows:
  chrome.exe:
    find_by_exe: true
    on_top: true
    monitor: 2
    left: 0
    top: 0
    width: 0.5
    height: 1

  '- Firefox':
    monitor: 2
    left: 0.5
    top: 0
    width: 0.5
    height: 1
```

## Window Matching

- Default: key is matched against window title.
- `find_by_exe: true`: key is matched against executable name (for example, `chrome.exe`).

## Set Window On Top

Use `on_top: true` to request the window be moved to the top when it is processed.

```yaml
windows:
  chrome.exe:
    find_by_exe: true
    on_top: true
    monitor: 2
    left: 0
    top: 0
    width: 1
    height: 1
```

Notes:

- This is not persistent and can reset when the window is minimized or closed.
- Use `on_top: false` or omit the field to keep default behavior (of not changing the window ordering beyond necessary).

## Placement Values

For `left`, `top`, `width`, `height`:

- Integer values represent absolute pixels.
- Decimal values in `0<x<=1` are relative to monitor work area. (e.g., `.5` means half, `1` means full, `10` means 10 pixels)

Monitor indices are 1-based:

- Leftmost monitor is `1`.
- Indices increase from left to right.

## Maximized Windows

You can request maximized behavior with:

```yaml
windows:
  WindowsTerminal.exe:
    find_by_exe: true
    monitor: 1
    maximized: true
```
