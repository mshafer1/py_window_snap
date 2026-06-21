import pathlib as _pathlib

import decouple as _decouple

_config = _decouple.AutoConfig(search_path=_pathlib.Path.cwd())

CONFIG_DIR: _pathlib.Path = _config(
    "WINDOW_SNAP_CONFIG_DIR",
    default=_pathlib.Path.home() / ".config" / "window-snap",
    cast=_pathlib.Path,
)

CONFIG_VERSION = "0.1.0"
