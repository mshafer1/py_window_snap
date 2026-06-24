"""Main entry point for the window_snap command-line tool."""

import logging

import click
import yaml

import window_snap
import window_snap._conf

_logger = logging.getLogger(__name__)


@click.command()
@click.version_option()
@click.option(
    "verbosity",
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (can be used multiple times)",
)
@click.option(
    "--store-current",
    is_flag=True,
    help="Store the current position and size of all windows in the config file instead of snapping",
)
@click.option(
    "--force",
    is_flag=True,
    help="Run even when the current session is a Windows remote desktop session",
)
def main(verbosity: int, store_current: bool, force: bool):
    """Snap windows to desired locations.

    Load window positions/sizes from a config file and snap windows accordingly,
    or store current positions/sizes if --store-current is used.
    """
    my_handler = logging.StreamHandler()
    logging_level = logging.WARNING - (10 * verbosity) if verbosity > 0 else logging.WARNING
    my_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root_logger = logging.getLogger(None)
    root_logger.setLevel(logging_level)
    root_logger.addHandler(my_handler)
    _logger.debug("Debug logging enabled")  # this will only show if verbosity is set to 2 or higher

    config_path = window_snap._conf.CONFIG_DIR / "config.yaml"

    if store_current:
        _logger.info("Storing current window positions and sizes to %s", config_path)
        current_windows = window_snap.get_current_windows()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        exe_names = window_snap.find_exe_names()
        with open(config_path, "w") as f:
            yaml.dump(
                {
                    "_config_version": window_snap._conf.CONFIG_VERSION,
                    "windows": current_windows,
                    "available_exe_names": exe_names,
                },
                f,
                Dumper=yaml.SafeDumper,
            )
        _logger.info("Current window positions and sizes stored successfully")
        return
    else:
        if window_snap._win32_helpers.is_remote_desktop_session() and not force:
            _logger.warning(
                "Remote desktop session detected; skipping window snapping. Use --force to override."
            )
            return

        _logger.info("Loading configuration from %s", config_path)
        config = window_snap.load_config(config_path)

        window_snap.snap_windows(config)


if __name__ == "__main__":
    main()
