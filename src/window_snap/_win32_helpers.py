import ctypes
import ctypes.wintypes
import difflib
import os
import time
import typing

import win32api
import win32con
import win32gui
import win32process

# Toolhelp constants
TH32CS_SNAPPROCESS = 0x00000002
SM_REMOTESESSION = 0x1000


if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32


class PROCESSENTRY32W(ctypes.Structure):
    """Structure for process entry used with CreateToolhelp32Snapshot."""

    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("cntUsage", ctypes.wintypes.DWORD),
        ("th32ProcessID", ctypes.wintypes.DWORD),
        ("th32DefaultHeapID", ULONG_PTR),
        ("th32ModuleID", ctypes.wintypes.DWORD),
        ("cntThreads", ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase", ctypes.wintypes.LONG),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def enum_windows() -> typing.List[typing.Dict]:
    """Enumerate visible top-level windows.

    Returns:
        List[Dict]: A list of window dictionaries containing hwnd, title, pid, and rect.
    """
    results = []

    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        try:
            title = win32gui.GetWindowText(hwnd).strip()
        except Exception:
            title = ""
        if not title:
            return True
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            x1, y1, x2, y2 = rect
            width = x2 - x1
            height = y2 - y1
            if width <= 10 or height <= 10:
                return True
            results.append(
                {"hwnd": hwnd, "title": title, "pid": pid, "rect": (x1, y1, width, height)}
            )
        except Exception:
            pass
        return True

    win32gui.EnumWindows(_cb, None)
    return results


def get_window_rect(hwnd: int) -> typing.Tuple[int, int, int, int]:
    """Return the window rectangle in left/top/width/height format.

    Args:
        hwnd (int): Handle to the target window.

    Returns:
        Tuple[int, int, int, int]: A tuple of (left, top, width, height).
    """
    x1, y1, x2, y2 = win32gui.GetWindowRect(hwnd)
    return x1, y1, x2 - x1, y2 - y1


def get_monitor_work_area_at_point(x: int, y: int) -> typing.Tuple[int, int, int, int]:
    """Return the work area rectangle for the monitor containing a point.

    Args:
        x (int): X coordinate of the point.
        y (int): Y coordinate of the point.

    Returns:
        Tuple[int, int, int, int]: A tuple of (left, top, width, height) for the monitor work area.
    """
    hmonitor = win32api.MonitorFromPoint((x, y), win32con.MONITOR_DEFAULTTONEAREST)
    info = win32api.GetMonitorInfo(hmonitor)
    left, top, right, bottom = info["Work"]
    return left, top, right - left, bottom - top


def set_window_pos(
    hwnd: int, left: int, top: int, width: int, height: int, activate: bool = False
) -> None:
    """Position and resize a window without changing its z-order.

    Args:
        hwnd (int): Handle to the target window.
        left (int): New left position.
        top (int): New top position.
        width (int): New window width.
        height (int): New window height.
        activate (bool): If True, activate the window after moving it.
    """
    flags = win32con.SWP_NOZORDER | win32con.SWP_NOOWNERZORDER
    if not activate:
        flags |= win32con.SWP_NOACTIVATE
    win32gui.SetWindowPos(hwnd, None, left, top, width, height, flags)


def is_remote_desktop_session() -> bool:
    """Return whether the current process is running in a remote desktop session."""
    try:
        if ctypes.windll.user32.GetSystemMetrics(SM_REMOTESESSION):
            return True
    except Exception:
        pass

    session_name = os.environ.get("SESSIONNAME", "")
    return session_name.upper().startswith("RDP-")


# Simple TTL cache for pid->exe mapping
_pid_exe_cache: typing.Dict[int, typing.Tuple[str, float]] = {}
_cache_ttl_seconds = 2.0


def _build_pid_to_exe_map() -> typing.Dict[int, str]:
    kernel32 = ctypes.windll.kernel32

    # Set proper argtypes/restype so HANDLE values are not truncated on 64-bit Python
    kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = ctypes.wintypes.BOOL
    kernel32.Process32NextW.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = ctypes.wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel32.CloseHandle.restype = ctypes.wintypes.BOOL

    invalid_handle_value = ctypes.c_void_p(-1).value
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == invalid_handle_value or snapshot is None:
        raise RuntimeError("CreateToolhelp32Snapshot failed")

    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    pid_to_exe: typing.Dict[int, str] = {}

    try:
        success = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while success:
            pid = entry.th32ProcessID
            exe = entry.szExeFile
            pid_to_exe[pid] = exe
            success = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)

    return pid_to_exe


def get_pid_to_exe_map(force_refresh: bool = False) -> typing.Dict[int, str]:
    """Return a cached mapping of process IDs to executable names.

    Args:
        force_refresh (bool): If True, rebuild the process map even if the cache is fresh.

    Returns:
        Dict[int, str]: A mapping from PID to executable filename.
    """
    global _pid_exe_cache
    now = time.time()
    if force_refresh:
        _pid_exe_cache.clear()
    # If cache empty or expired, rebuild
    if not _pid_exe_cache or any(
        now - ts > _cache_ttl_seconds for _, ts in _pid_exe_cache.values()
    ):
        pid_map = _build_pid_to_exe_map()
        _pid_exe_cache = {pid: (exe, now) for pid, exe in pid_map.items()}
    return {pid: exe for pid, (exe, ts) in _pid_exe_cache.items()}


def find_hwnds_by_title(title: str) -> typing.List[int]:
    """Return visible top-level window handles matching a title query.

    Uses difflib.get_close_matches to sort candidate titles by similarity.

    Args:
        title (str): Window title query.

    Returns:
        List[int]: Matching window handles sorted by closest title matches.
    """
    query = title.strip()
    if not query:
        return []

    title_to_hwnds: typing.Dict[str, typing.List[int]] = {}

    def _cb(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            t = win32gui.GetWindowText(hwnd).strip()
            if not t:
                return True
            title_to_hwnds.setdefault(t, []).append(hwnd)
        except Exception:
            pass
        return True

    win32gui.EnumWindows(_cb, None)
    if not title_to_hwnds:
        return []

    ordered_titles = difflib.get_close_matches(
        query, list(title_to_hwnds.keys()), n=len(title_to_hwnds), cutoff=0.0
    )

    # Keep exact-match titles first when present.
    if query in title_to_hwnds:
        ordered_titles = [query] + [t for t in ordered_titles if t != query]

    ordered_hwnds: typing.List[int] = []
    for matched_title in ordered_titles:
        ordered_hwnds.extend(title_to_hwnds.get(matched_title, []))
    return ordered_hwnds


def find_hwnds_by_exe(exe_name: str) -> typing.List[int]:
    """Return window handles for processes matching an executable name.

    This normalizes names by stripping paths and extensions so callers can pass
    either 'chrome', 'chrome.exe', or a full path.

    Args:
        exe_name (str): Executable name or path to match.

    Returns:
        List[int]: List of matching window handles.
    """

    def _norm(n: str) -> str:
        if not n:
            return ""
        # if a bytes-like got here, convert
        try:
            n = str(n)
        except Exception:
            pass
        base = os.path.basename(n)
        name, _ext = os.path.splitext(base)
        return name.lower()

    pid_map = get_pid_to_exe_map()
    target_pids = {pid for pid, exe in pid_map.items() if _norm(exe) == _norm(exe_name)}
    if not target_pids:
        return []
    matches: typing.List[int] = []
    def _cb(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in target_pids:
                matches.append(hwnd)
        except Exception:
            pass
        return True

    win32gui.EnumWindows(_cb, None)
    return matches
