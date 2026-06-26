# Installation

This project is distributed as a Python CLI package.

## Option 1: Install with pipx (recommended)

`pipx` installs command-line Python tools in isolated environments.

```powershell
pipx install window_snap
```

After installation, verify the command is available:

```powershell
window-snap --version
```

## Option 2: Local Development Install

If you are working from source:

```powershell
# from the repository root
pip install -e .
```

This installs the CLI entry point `window-snap` from your local checkout.

## Configuration File Location

By default, window-snap looks for:

```text
%USERPROFILE%\.config\window-snap\config.yaml
```

To use a different config directory, set this environment variable:

```text
WINDOW_SNAP_CONFIG_DIR
```

Example in PowerShell:

```powershell
$env:WINDOW_SNAP_CONFIG_DIR = "C:\Users\YourUser\my-window-snap-config"
```
