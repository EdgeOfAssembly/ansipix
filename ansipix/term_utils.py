"""
term_utils.py - Terminal Utility Functions

This module provides cross-platform functions for interacting with the terminal,
such as detecting font metrics and pixel dimensions. This is essential for
correctly calculating aspect ratios for media rendering. It handles the
differences between Windows and Unix-like (Linux, macOS) systems.
"""
import sys
import os
import subprocess
import ctypes
from ctypes import wintypes
import array
import fcntl
import termios
import tty
import shutil
from typing import Tuple

# Windows-specific structures and functions for font detection
if os.name == 'nt':
    class COORD(ctypes.Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

    class CONSOLE_FONT_INFOEX(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.ULONG),
            ("nFont", wintypes.SHORT),
            ("FontSize", COORD),
            ("FontFamily", wintypes.USHORT),
            ("FontWeight", wintypes.USHORT),
            ("FaceName", wintypes.WCHAR * 32)
        ]

def get_terminal_pixel_size() -> Tuple[int, int]:
    """
    Gets the terminal size in pixels using ANSI escape codes.
    This is a fallback method for Unix-like systems.
    
    Returns:
        A tuple (height, width) in pixels.
    """
    if not sys.stdout.isatty():
        return 0, 0
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write('\033[14t')
        sys.stdout.flush()
        response = b''
        while True:
            ch = os.read(fd, 1)
            response += ch
            if ch == b't':
                break
        # Response format: \033[4;height;widtht
        if response.startswith(b'\033[4;') and response.endswith(b't'):
            parts = response[4:-1].decode('utf-8').split(';')
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return 0, 0

def get_current_font() -> Tuple[str, int, int]:
    """
    Detects the current terminal font name and size (width, height) in pixels.
    
    Returns:
        A tuple (font_name, font_width, font_height).
    """
    if os.name == 'nt':  # Windows
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
            font = CONSOLE_FONT_INFOEX()
            font.cbSize = ctypes.sizeof(CONSOLE_FONT_INFOEX)
            if kernel32.GetCurrentConsoleFontEx(handle, False, ctypes.byref(font)):
                return font.FaceName.rstrip('\x00'), font.FontSize.X, font.FontSize.Y
        except Exception:
            return "N/A", 0, 0
        return "N/A", 0, 0
    else:  # Unix-like systems
        font_family, font_width, font_height = "N/A", 0, 0
        try:
            output = subprocess.check_output(['fc-match', 'monospace'], text=True).strip()
            if ':' in output:
                font_part = output.split(':', 1)[1].strip()
                font_family = font_part.split('"')[1] if '"' in font_part else font_part
        except Exception:
            font_family = "Monospace"

        term_size = shutil.get_terminal_size(fallback=(80, 24))
        rows, cols = term_size.lines, term_size.columns

        try:
            # Try ioctl first, as it's the most reliable method
            buf = array.array('H', [0, 0, 0, 0])
            if fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, buf) == 0:
                _, _, xpixels, ypixels = buf
                if cols > 0 and xpixels > 0: font_width = xpixels // cols
                if rows > 0 and ypixels > 0: font_height = ypixels // rows
        except Exception:
            pass

        # Fallback to escape sequence if ioctl failed or returned zeros
        if font_width == 0 or font_height == 0:
            pixel_h, pixel_w = get_terminal_pixel_size()
            if pixel_w > 0 and cols > 0: font_width = pixel_w // cols
            if pixel_h > 0 and rows > 0: font_height = pixel_h // rows
                
        return font_family, font_width, font_height

def supports_truecolor() -> bool:
    """Checks if the terminal likely supports 24-bit truecolor."""
    colorterm = os.environ.get('COLORTERM', '').lower()
    return colorterm in ['truecolor', '24bit']