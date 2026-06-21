import collections
import dataclasses
import functools
import logging
import os
import time
import typing

import screeninfo
import yaml

import window_snap
from . import win32_helpers
import win32con
import win32gui

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
    for w in win32_helpers.enum_windows():
        title = w.get("title")
        rect = w.get("rect")
        if not title:
            continue
        pos_args = {}
        # rect is (left, top, width, height)
        if rect:
            left, top, width, height = rect
            # treat very large windows as maximized heuristically
            if width == 0 or height == 0:
                pos_args["maximized"] = True
            else:
                pos_args.update({"left": left, "top": top, "width": width, "height": height})
        current_windows[title] = WindowSnapDestination(**pos_args)
    return current_windows


def find_exe_names():
    title_to_exe_map = {}
    try:
        pid_map = win32_helpers.get_pid_to_exe_map()
        for w in win32_helpers.enum_windows():
            title = w.get("title")
            pid = w.get("pid")
            if title and pid:
                exe = pid_map.get(pid)
                if exe:
                    title_to_exe_map[title] = exe.lower()
    except Exception as e:
        _logger.debug("failed get exe names via win32 helpers: %s", e)
    return title_to_exe_map


@functools.lru_cache(maxsize=1)
def find_pid_for_exe():
    exe_to_pid = collections.defaultdict(list)
    try:
        pid_map = win32_helpers.get_pid_to_exe_map()
        for pid, exe in pid_map.items():
            exe_to_pid[exe].append(pid)
    except Exception as e:
        _logger.debug("failed build pid map via Toolhelp: %s", e)
    return exe_to_pid


def _find_monitor_by_rect(left: int, top: int, width: int, height: int):
    win_center_x = left + (width // 2)
    win_center_y = top + (height // 2)

    monitors = _get_screen_info()
    for index, monitor in enumerate(monitors):
        inside_x = monitor.x <= win_center_x < (monitor.x + monitor.width)
        inside_y = monitor.y <= win_center_y < (monitor.y + monitor.height)
        if inside_x and inside_y:
            return index, monitor

    _logger.warning("Could not determine monitor for rect %s,%s %sx%s", left, top, width, height)
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
        hwnd = None
        if destination.find_by_exe:
            # window_title here is expected to be an exe name
            hwnds = win32_helpers.find_hwnds_by_exe(window_title)
            if not hwnds:
                _logger.warning("No window found for exe '%s', skipping", window_title)
                return
            hwnd = hwnds[0]
        else:
            hwnds = win32_helpers.find_hwnds_by_title(window_title)
            if not hwnds:
                _logger.info("Window '%s' not found, skipping", window_title)
                return
            hwnd = hwnds[0]
    except IndexError:
        _logger.info("Window '%s' not found, skipping", window_title)
        return
    # ensure window is not minimized or maximized before moving/resizing
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    except Exception:
        pass

    # Perform the window snapping logic here
    _logger.info("Window '%s' found (hwnd=%s), snapping to destination: %s", window_title, hwnd, destination)
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
        work_left, work_top, work_width, work_height = win32_helpers.get_monitor_work_area_at_point(
            screen.x + 1, screen.y + 1
        )

        if destination.maximized:
            try:
                win32gui.SetWindowPos(hwnd, None, work_left, work_top, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            except Exception:
                pass
        else:
            left, top, width, height = (
                _scale_to_dimension(v, dimension, pos)
                for v, dimension, pos in [
                    (destination.left, work_width, work_left),
                    (destination.top, work_height, work_top),
                    (destination.width, work_width, 0),
                    (destination.height, work_height, 0),
                ]
            )

            _logger.debug("Handling %s as %s", destination, (left, top, width, height))
            if left is not None and top is not None and width is not None and height is not None:
                win32_helpers.set_window_pos(hwnd, left, top, width, height, activate=False)
            else:
                # partial updates
                try:
                    cur_left, cur_top, cur_w, cur_h = win32_helpers.get_window_rect(hwnd)
                    nl = left if left is not None else cur_left
                    nt = top if top is not None else cur_top
                    nw = width if width is not None else cur_w
                    nh = height if height is not None else cur_h
                    win32_helpers.set_window_pos(hwnd, nl, nt, nw, nh, activate=False)
                except Exception:
                    pass
    else:
        # no monitor specified, just apply position/size changes
        if destination.maximized:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            except Exception:
                pass
        else:
            try:
                cur_left, cur_top, cur_w, cur_h = win32_helpers.get_window_rect(hwnd)
                monitor_info = _find_monitor_by_rect(cur_left, cur_top, cur_w, cur_h)
                if monitor_info is None:
                    _logger.debug("Could not determine monitor for hwnd %s, using primary monitor", hwnd)
                    monitor = screens[0]
                    work_left, work_top, work_width, work_height = win32_helpers.get_monitor_work_area_at_point(
                        monitor.x + 1, monitor.y + 1
                    )
                else:
                    _, monitor = monitor_info
                    work_left, work_top, work_width, work_height = win32_helpers.get_monitor_work_area_at_point(
                        cur_left + 1, cur_top + 1
                    )

                left, top, width, height = (
                    _scale_to_dimension(v, dimension, pos)
                    for v, dimension, pos in [
                        (destination.left, work_width, work_left),
                        (destination.top, work_height, work_top),
                        (destination.width, work_width, 0),
                        (destination.height, work_height, 0),
                    ]
                )

                _logger.debug("Handling %s as %s", destination, (left, top, width, height))
                if left is not None and top is not None and width is not None and height is not None:
                    win32_helpers.set_window_pos(hwnd, left, top, width, height, activate=False)
                else:
                    cur_left, cur_top, cur_w, cur_h = win32_helpers.get_window_rect(hwnd)
                    nl = left if left is not None else cur_left
                    nt = top if top is not None else cur_top
                    nw = width if width is not None else cur_w
                    nh = height if height is not None else cur_h
                    win32_helpers.set_window_pos(hwnd, nl, nt, nw, nh, activate=False)
            except Exception as e:
                _logger.debug("failed to reposition hwnd %s: %s", hwnd, e)


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
