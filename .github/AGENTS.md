# AGENTS

## Project Summary

window-snap is a Windows command-line tool that applies window layout rules from a YAML config file.

It supports:
- Matching windows by title or executable name.
- Positioning and resizing windows using absolute or fractional values.
- Multi-monitor placement with a 1-based monitor index.
- Maximizing windows.
- Optional temporary on-top behavior.

## Installation

Recommended:

```powershell
pipx install window_snap
```

From source:

```powershell
pip install -e .
```

## Configuration

Default config path:

```text
%USERPROFILE%\.config\window-snap\config.yaml
```

Override config directory with:

```text
WINDOW_SNAP_CONFIG_DIR
```

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

## Command Usage

Apply configured layout:

```powershell
window-snap
```

Capture current window positions into config:

```powershell
window-snap --store-current
```

Force snapping in a Remote Desktop session:

```powershell
window-snap --force
```

Increase logging:

```powershell
window-snap -v
window-snap -vv
```

## Notes

- Monitor numbering in config is 1-based.
- `on_top` behavior is temporary and may reset when the window is minimized or closed.
- When updating documentation, keep both `docs/` and `README.md` in sync.
