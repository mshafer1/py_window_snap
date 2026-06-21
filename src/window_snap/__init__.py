import collections
import dataclasses
import functools
import logging
import os
import time
import typing

import pyautogui
import pywinauto
import screeninfo
import yaml

import window_snap
from window_snap.__main__ import _logger

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())  # make sure there is a default handler available


def load_config(config_path: str) -> dict:
    try:
        with open(config_path, "r") as f:
            config = yaml.load(f, Loader=yaml.CSafeLoader)
        return config
    except FileNotFoundError:
        _logger.warning("Config file not found: %s", config_path)
        return {}
    except yaml.YAMLError as e:
        _logger.error("Error parsing config file %s: %s", config_path, e)
        raise


@functools.lru_cache(maxsize=1)
def _get_screen_info() -> typing.List[screeninfo.screeninfo.Monitor]:
    return list(sorted(screeninfo.screeninfo.get_monitors(), key=lambda m: (m.x, m.y)))


def dataclass_representer(dumper, data):
    # This automatically converts the dataclass to a plain dict behind the scenes
    return dumper.represent_dict({k: v for k, v in data._asdict().items() if v is not None})



class WindowSnapDestination(typing.NamedTuple):
    monitor: typing.Optional[int] = None
    left: typing.Optional[float] = None
    top: typing.Optional[float] = None
    width: typing.Optional[float] = None
    height: typing.Optional[float] = None
    maximized: typing.Optional[bool] = None
    find_by_exe: typing.Optional[bool] = None


yaml.SafeDumper.add_multi_representer(WindowSnapDestination, dataclass_representer)


def get_current_windows() -> typing.Dict[str, WindowSnapDestination]:
    current_windows = {}
    for window in pyautogui.getAllWindows():
        # TODO: if there is more then one monitor, also store that.
        if window.title:
            pos_args = {}
            if window.isMaximized:
                pos_args["maximized"] = True
            else:
                pos_args.update(
                    {
                        "left": window.left,
                        "top": window.top,
                        "width": window.width,
                        "height": window.height,
                    }
                )
            current_windows[window.title] = WindowSnapDestination(**pos_args)
    return current_windows


def find_exe_names():
    title_to_exe_map = {}

    # Get all running processes
    try:
        all_running_modules = pywinauto.application.process_get_modules()
    except Exception as e:
        print(f"Error accessing system modules: {e}. Try running as Admin.")
        return {}

    # Convert the module list into a fast lookup dictionary: { pid: "filename.exe" }
    pid_to_exe = {}
    for pid, exe_path, *_ in all_running_modules:
        pid_to_exe[pid] = os.path.basename(exe_path).lower()

    # grab open windows
    windows = pywinauto.Desktop(backend="win32").windows()

    for w in windows:
        try:
            # Pull the title text string
            title = w.texts()[0].strip() if w.texts() else ""

            # Filter out hidden tool overlays or broken zero-sized elements
            rect = w.rectangle()
            has_size = rect.width() > 10 and rect.height() > 10

            if w.is_visible() and title and has_size:
                win_pid = w.process_id()

                # Store title -> exe name using pid
                if win_pid in pid_to_exe:
                    exe_name = pid_to_exe[win_pid]
                    title_to_exe_map[title] = exe_name
        except Exception as e:
            _logger.debug("failed get info for a window: %s, continuing", e)
    return title_to_exe_map


@functools.lru_cache(maxsize=1)
def find_pid_for_exe():
    exe_to_pid = collections.defaultdict(list)

    # Get all running processes
    try:
        all_running_modules = pywinauto.application.process_get_modules()
    except Exception as e:
        print(f"Error accessing system modules: {e}. Try running as Admin.")
        return {}

    for pid, exe_path, *_ in all_running_modules:
        exe_to_pid[os.path.basename(exe_path)].append(pid)

    # grab open windows
    return exe_to_pid


def _find_monitor(window):
    win_center_x = window.left + (window.width // 2)
    win_center_y = window.top + (window.height // 2)

    monitors = _get_screen_info()
    for index, monitor in enumerate(monitors):
        # Check if center X is between monitor left and monitor right
        inside_x = monitor.x <= win_center_x < (monitor.x + monitor.width)
        # Check if center Y is between monitor top and monitor bottom
        inside_y = monitor.y <= win_center_y < (monitor.y + monitor.height)

        if inside_x and inside_y:
            return index, monitor

    _logger.warning("Could not determine monitor for window %s", window.title)
    return None


def _scale_to_dimension(value: typing.Union[float, int, None], dimension: int, base: int):
    if value is None:
        return None
    if 0 < value <= 1:  # it's a float. 0 means "at the point", 0<x<1 is percentage. 1 is full. Anything other then that is a pixel value.
        return int(value * dimension) + base
    else:  # absolute value integer
        return int(value) + base


def snap_window(window_title: str, destination: WindowSnapDestination):
    _logger.info("Snapping window '%s' to destination: %s", window_title, destination)

    try:
        if destination.find_by_exe:
            main_window = None
            try:
                app = pywinauto.Application().connect(path=window_title)
                main_window = app.top_window()
            except:
                pass
            if main_window is None:
                pid_options = find_pid_for_exe().get(window_title)
                if not pid_options:
                    _logger.warning("No window found for '%s', skipping", window_title)
                    return
                app = pywinauto.Application().connect(process=pid_options[0])
                main_window = app.top_window()
            main_window.set_focus()
            time.sleep(0.1)
            window = pyautogui.getActiveWindow()
        else:
            window = pyautogui.getWindowsWithTitle(window_title)[0]
    except IndexError:
        _logger.info("Window '%s' not found, skipping", window_title)
        return

    window.restore()  # ensure window is not minimized or maximized before moving/resizing
    time.sleep(0.1)  # give the window manager a moment to update the window state

    # Perform the window snapping logic here
    # This is a placeholder - replace with actual window snapping implementation
    _logger.info("Window '%s' found, snapping to destination: %s", window_title, destination)
    screens = _get_screen_info()

    if destination.monitor is not None and destination.monitor >= len(screens):
        _logger.warning(
            "Monitor index %d is out of range, skipping monitor assignment", destination.monitor
        )
        destination = dataclasses.replace(destination, monitor=None)

    if destination.monitor is not None:
        # move to desired monitor
        if destination.monitor >= len(screens):
            _logger.warning(
                "Monitor index %d is out of range, skipping monitor assignment", destination.monitor
            )
            return

        screen = screens[destination.monitor]
        if destination.maximized:
            window.moveTo(screen.x, screen.y)
            window.maximize()
        else:
            left, top, width, height = (
                _scale_to_dimension(v, dimension, pos)
                for v, dimension, pos in [
                    (destination.left, screen.width, screen.x),
                    (destination.top, screen.height, screen.y),
                    (destination.width, screen.width, 0),
                    (destination.height, screen.height, 0),
                ]
            )

            _logger.debug("Handling %s as %s", destination, (left, top, width, height))
            if left is not None and top is not None:
                window.moveTo(left, top)
            if width is not None and height is not None:
                window.resizeTo(width, height)
    else:
        # no monitor specified, just apply position/size changes
        if destination.maximized:
            window.maximize()
        else:
            current_screen = _find_monitor(window)
            left, top, width, height = (
                _scale_to_dimension(v, dimension, pos)
                for v, dimension, pos in [
                    (destination.left, current_screen.width, current_screen.x),
                    (destination.top, current_screen.height, current_screen.y),
                    (destination.width, current_screen.width, 0),
                    (destination.height, current_screen.height, 0),
                ]
            )

            _logger.debug("Handling %s as %s", destination, (left, top, width, height))
            if left is not None and top is not None:
                window.moveTo(left, top)
            if width is not None and height is not None:
                window.resizeTo(width, height)


def snap_windows(config):
    for window_name, snap_config in config["windows"].items():
        _logger.debug("Processing window '%s' with config: %s", window_name, snap_config)
        try:
            destination = window_snap.WindowSnapDestination(
                **{
                    k: v
                    for k, v in snap_config.items()
                    if k in window_snap.WindowSnapDestination._fields
                }
            )
        except TypeError as e:
            _logger.error(
                "Invalid configuration for window '%s': %s. Error: %s", window_name, snap_config, e
            )
            continue
        try:
            window_snap.snap_window(window_name, destination)
        except Exception as e:
            _logger.error("Error occurred while snapping window '%s': %s", window_name, e)
