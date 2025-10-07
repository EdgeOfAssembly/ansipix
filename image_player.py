"""
image_player.py - Image and GIF Playback

This module handles the live playback of static images and animated GIFs.
It contains a more complex rendering pipeline than the video player, as it needs
to manage features like background colors/images, transparency blending, and
centering the image within the terminal.

NOTE: This module has its own rendering logic. A future improvement would be to
refactor this to use the more optimized renderer from `render.py`.
"""
import argparse
import sys
import os
import shutil
import signal
import time
from typing import Tuple, List, Optional, Any, Dict
import numpy as np
import cv2
from PIL import Image, ImageSequence
from bisect import bisect_left
from dimensions import calculate_dimensions
from debug_logger import DebugLogger

# --- Constants ---
_PIXEL_PER_CHAR_W = 1
_PIXEL_PER_CHAR_H = 2
_HIDE_CURSOR, _SHOW_CURSOR = "\033[?25l", "\033[?25h"
_ALT_BUFFER_ENTER, _ALT_BUFFER_EXIT = "\033[?1049h", "\033[?1049l"
_CLEAR_SCREEN, _RESET = "\033[2J\033[H", "\033[0m"
_UPPER_BLOCK = "▀"
_COLOR_DICT: Dict[str, Tuple[int, int, int]] = { 'black': (0,0,0), 'white': (255,255,255), 'red': (255,0,0), 'green': (0,255,0), 'blue': (0,0,255), 'yellow': (255,255,0), 'magenta': (255,0,255), 'cyan': (0,255,255) }
_INTERPOLATION_MAP: Dict[str, int] = { 'nearest': cv2.INTER_NEAREST, 'linear': cv2.INTER_LINEAR, 'cubic': cv2.INTER_CUBIC, 'area': cv2.INTER_AREA, 'lanczos4': cv2.INTER_LANCZOS4 }

def _detect_terminal_size() -> Tuple[int, int]:
    try:
        return shutil.get_terminal_size(fallback=(80, 24))
    except OSError:
        return 80, 24

def _parse_background(bg_arg: str, tile: bool, term_w: int, term_h: int, interpolation: int) -> Tuple[Optional[np.ndarray], Tuple[int, int, int]]:
    """Parses the --background argument into either a background image or a solid color."""
    if bg_arg.lower() in _COLOR_DICT:
        return None, _COLOR_DICT[bg_arg.lower()]
    if len(bg_arg) == 6 and all(c in '0123456789abcdef' for c in bg_arg.lower()):
        try:
            r, g, b = int(bg_arg[0:2], 16), int(bg_arg[2:4], 16), int(bg_arg[4:6], 16)
            return None, (r, g, b)
        except ValueError:
            pass

    try:
        bg_img_bgr = cv2.imread(bg_arg, cv2.IMREAD_UNCHANGED)
        if bg_img_bgr is None: raise FileNotFoundError
        bg_img_rgba = cv2.cvtColor(bg_img_bgr, cv2.COLOR_BGRA2RGBA if bg_img_bgr.shape[2] == 4 else cv2.COLOR_BGR2RGBA)
        bg_pixel_w, bg_pixel_h = term_w * _PIXEL_PER_CHAR_W, term_h * _PIXEL_PER_CHAR_H
        if tile:
            num_tiles_across = 4
            tile_w = bg_pixel_w // num_tiles_across
            tile_h = int(tile_w * (bg_img_rgba.shape[0] / bg_img_rgba.shape[1])) if bg_img_rgba.shape[1] > 0 else 0
            if tile_w == 0 or tile_h == 0: raise IOError("Terminal too small for tiling.")
            tile_resized = cv2.resize(bg_img_rgba, (tile_w, tile_h), interpolation=interpolation)
            num_y, num_x = (bg_pixel_h + tile_h - 1) // tile_h, (bg_pixel_w + tile_w - 1) // tile_w
            tiled_canvas = np.tile(tile_resized, (num_y, num_x, 1))
            return tiled_canvas[:bg_pixel_h, :bg_pixel_w, :], (0, 0, 0)
        else:
            return cv2.resize(bg_img_rgba, (bg_pixel_w, bg_pixel_h), interpolation=interpolation), (0, 0, 0)
    except (FileNotFoundError, IOError, cv2.error):
        print(f"Warning: Background '{bg_arg}' is not a valid color or image file. Defaulting to black.", file=sys.stderr)
        return None, (0, 0, 0)

def _render_to_ansi(pixel_data: np.ndarray) -> str:
    """Renders a pixel buffer to a single ANSI string. (Internal to image_player)."""
    height, width, channels = pixel_data.shape
    if channels == 4:
        alpha = pixel_data[:, :, 3, np.newaxis] / 255.0
        pixel_data = (pixel_data[:, :, :3] * alpha).astype(np.uint8)
    top_pixels, bot_pixels = pixel_data[0::2, :, :], pixel_data[1::2, :, :]
    output_lines = []
    for y in range(top_pixels.shape[0]):
        line, last_fg, last_bg = [], None, None
        for x in range(width):
            fg, bg = tuple(top_pixels[y, x]), tuple(bot_pixels[y, x])
            if fg != last_fg or bg != last_bg:
                line.append(f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m\033[48;2;{bg[0]};{bg[1]};{bg[2]}m")
                last_fg, last_bg = fg, bg
            line.append(_UPPER_BLOCK)
        output_lines.append("".join(line))
    return _RESET + ("\n" + _RESET).join(output_lines)

def play_image_animation(args: argparse.Namespace, image_path: str, logger: DebugLogger) -> None:
    """Main function for displaying static images and animated GIFs."""
    term_w, term_h = _detect_terminal_size()
    background_arg = args.background if args.background is not None else 'black'
    interpolation = _INTERPOLATION_MAP.get(getattr(args, 'downsample_method', 'area'), cv2.INTER_AREA)

    bg_image_data, bg_solid_color = _parse_background(background_arg, args.tile, term_w, term_h, interpolation)
    
    def signal_handler(sig: int, frame: Any) -> None:
        print(_ALT_BUFFER_EXIT + _SHOW_CURSOR + _RESET)
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(_ALT_BUFFER_ENTER + _HIDE_CURSOR)
    if bg_image_data is not None:
        print(f"\033[H{_render_to_ansi(bg_image_data)}", end="")
    else:
        r, g, b = bg_solid_color
        print(f"\033[48;2;{r};{g};{b}m{_CLEAR_SCREEN}", end="")
    sys.stdout.flush()

    try:
        img_pil = Image.open(image_path)
        orig_w, orig_h = img_pil.size
        target_char_w, target_char_h, target_pixel_w, target_pixel_h = calculate_dimensions(orig_w, orig_h, term_w, term_h)
        logger.log(f"Resizing to {target_pixel_w}x{target_pixel_h} pixels ({target_char_w}x{target_char_h} chars)")

        frames_data, durations = [], []
        for frame_pil in ImageSequence.Iterator(img_pil):
            frame_rgba = np.array(frame_pil.convert("RGBA"))
            resized_np = cv2.resize(frame_rgba, (target_pixel_w, target_pixel_h), interpolation=interpolation)
            frames_data.append(resized_np)
            durations.append(frame_pil.info.get('duration', 100) / 1000.0)
        n_frames = len(frames_data)

    except (FileNotFoundError, ValueError) as e:
        print(f"{_ALT_BUFFER_EXIT}{_SHOW_CURSOR}{_RESET}Error: Could not load image '{image_path}'. {e}", file=sys.stderr)
        sys.exit(1)

    start_col, start_row = (term_w - target_char_w) // 2 + 1, (term_h - target_char_h) // 2 + 1
    total_duration = sum(durations) if n_frames > 1 else float('inf')
    cumulative_times = np.cumsum([0] + durations)
    start_time, last_frame_idx, loop_count = time.perf_counter(), -1, 0

    while True:
        if args.loop > 0 and loop_count >= args.loop: break
        
        elapsed = (time.perf_counter() - start_time) % total_duration if total_duration != float('inf') else 0
        current_loop = (time.perf_counter() - start_time) // total_duration if total_duration != float('inf') else 0
        
        if current_loop > loop_count:
            loop_count = int(current_loop)
            if args.loop > 0 and loop_count >= args.loop: break

        frame_idx = bisect_left(cumulative_times, elapsed) - 1 if total_duration != float('inf') else 0
        frame_idx = max(0, frame_idx)

        if frame_idx != last_frame_idx:
            render_start_time = time.perf_counter()
            canvas_h, canvas_w = target_pixel_h, target_pixel_w
            
            if bg_image_data is not None:
                y_start, x_start = (start_row-1)*_PIXEL_PER_CHAR_H, (start_col-1)*_PIXEL_PER_CHAR_W
                canvas = bg_image_data[y_start:y_start+canvas_h, x_start:x_start+canvas_w, :3].copy()
            else:
                canvas = np.full((canvas_h, canvas_w, 3), bg_solid_color, dtype=np.uint8)

            frame_data = frames_data[frame_idx]
            alpha = frame_data[:, :, 3, np.newaxis] / 255.0
            blended_frame = (frame_data[:, :, :3] * alpha + canvas * (1 - alpha)).astype(np.uint8)
            frame_str = _render_to_ansi(blended_frame)
            
            lines = frame_str.split('\n')
            output = [f"\033[{start_row + i};{start_col}H{line}" for i, line in enumerate(lines)]
            print("".join(output), end=""); sys.stdout.flush()
            last_frame_idx = frame_idx
            
            if logger.is_active and n_frames > 0:
                write_time = time.perf_counter() - render_start_time
                logger.log(f"Frame {frame_idx + 1}/{n_frames} write time: {write_time*1000:.1f}ms")

        if total_duration == float('inf'): break # Static image, break after one frame
            
        next_frame_time = cumulative_times[frame_idx + 1] if frame_idx + 1 < len(cumulative_times) else total_duration
        sleep_duration = next_frame_time - elapsed
        if sleep_duration > 0.001: time.sleep(sleep_duration)

    if total_duration == float('inf'):
        try: input() # Wait for user input for static images
        except (KeyboardInterrupt, EOFError): pass
    
    print(_ALT_BUFFER_EXIT + _SHOW_CURSOR + _RESET)