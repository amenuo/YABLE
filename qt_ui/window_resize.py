from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Any

IS_WINDOWS = sys.platform == "win32"

WM_NCHITTEST = 0x0084

HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

RESIZE_BORDER_LOGICAL_PX = 6


def nchittest_lparam(event_type: Any, message: Any) -> int | None:
    """Return the lParam of a WM_NCHITTEST message, or None for other messages."""
    if not IS_WINDOWS:
        return None
    try:
        if bytes(event_type) != b"windows_generic_MSG":
            return None
        msg = wintypes.MSG.from_address(int(message))
    except (TypeError, ValueError):
        return None
    if msg.message != WM_NCHITTEST:
        return None
    return int(msg.lParam)


def screen_point(lparam: int) -> tuple[int, int]:
    """Decode the signed screen coordinates packed into a mouse message lParam."""
    x = ctypes.c_short(lparam & 0xFFFF).value
    y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
    return int(x), int(y)


def window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Physical-pixel window bounds as (left, top, right, bottom)."""
    rect = wintypes.RECT()
    if not ctypes.windll.user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
        return None
    return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)


def resize_border(hwnd: int, logical_px: int = RESIZE_BORDER_LOGICAL_PX) -> int:
    """Scale the resize hot zone for the window's current DPI."""
    dpi = 0
    try:
        dpi = int(ctypes.windll.user32.GetDpiForWindow(wintypes.HWND(hwnd)))
    except (AttributeError, OSError):
        dpi = 0
    if dpi <= 0:
        dpi = 96
    return max(4, round(logical_px * dpi / 96))


def hit_test_resize(
    x: int,
    y: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    border: int,
) -> int | None:
    """Map a screen point to a Win32 resize hit code, or None for the client area."""
    near_left = x < left + border
    near_right = x >= right - border
    near_top = y < top + border
    near_bottom = y >= bottom - border

    if near_top and near_left:
        return HTTOPLEFT
    if near_top and near_right:
        return HTTOPRIGHT
    if near_bottom and near_left:
        return HTBOTTOMLEFT
    if near_bottom and near_right:
        return HTBOTTOMRIGHT
    if near_top:
        return HTTOP
    if near_bottom:
        return HTBOTTOM
    if near_left:
        return HTLEFT
    if near_right:
        return HTRIGHT
    return None
