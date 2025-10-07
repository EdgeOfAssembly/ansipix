"""
ansipix.py - Main Entry Point

This script serves as the primary controller for the ansipix application. It is responsible for:
- Parsing command-line arguments.
- Initializing the debug logger.
- Detecting the input file type (.ansipix or standard media).
- Dispatching the task to the appropriate handler:
  - `play_ansipix_file` for replaying pre-rendered animations.
  - `play_video` or `play_image_animation` for live rendering.
  - A multiprocessing-based offline renderer for creating .ansipix files.
- Handling the --profile argument to enable cProfile for performance analysis.
"""
import argparse
import sys
import os
import signal
import shutil
import json
import struct
from threading import Event
from typing import Optional

import cv2
import numpy as np

# Local imports
from .media_loader import load_media
from .animation_player import play_video, play_ansipix_file
from .dimensions import calculate_dimensions
from .image_player import play_image_animation
from .term_utils import get_current_font
from .debug_logger import DebugLogger

# Enable ANSI escape code processing on Windows
if os.name == 'nt':
    os.system('')

def main(args: argparse.Namespace) -> None:
    """
    Main controller function for the ansipix application.

    Orchestrates the loading, rendering, and playback of media based on user arguments.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
    """
    # --- Playback Logic ---
    # If the input is an .ansipix file, dispatch to the playback function and exit.
    if args.image_path.lower().endswith('.ansipix'):
        play_ansipix_file(args.image_path, args)
        return

    # --- Live Rendering or Offline Creation ---
    with DebugLogger(args.debug) as logger:
        try:
            term_w, term_h = shutil.get_terminal_size()
        except OSError:
            term_w, term_h = 80, 24
        # Reserve one line for potential user input or shell prompt
        effective_h = max(1, term_h - 1)

        if logger.is_active:
            # Log detailed system info if debugging is enabled
            font_family, font_w, font_h = get_current_font()
            pixel_w, pixel_h = term_w * font_w, effective_h * font_h
            char_aspect_ratio = 0.5

            logger.log("--- Terminal & System Info ---")
            logger.log(f"Terminal size: {term_w} cols x {term_h} rows")
            if font_w > 0 and font_h > 0:
                logger.log(f"Calculated render pixel size: {pixel_w} x {pixel_h}")
                logger.log(f"Detected font: '{font_family}' ({font_w}x{font_h} pixels per char)")
            else:
                logger.log("Could not detect font metrics. Aspect ratio may be incorrect.")
            logger.log(f"Using character aspect ratio for correction: {char_aspect_ratio}")
            logger.log("--------------------------------\n")

        is_video, _, durations, n_frames_from_loader, img, orig_w, orig_h = load_media(args.image_path, logger)
        
        # --- Offline .ansipix File Rendering Logic ---
        if args.output and args.output.lower().endswith('.ansipix'):
            # Lazy-import multiprocessing modules only when needed
            from multiprocessing import Pool, cpu_count
            from offline_renderer import render_frame_for_offline
            
            logger.log("Offline rendering to .ansipix format initiated.")
            
            t_char_w, t_char_h, t_pixel_w, t_pixel_h = calculate_dimensions(
                orig_w, orig_h, term_w, effective_h
            )
            
            raw_frames: list[np.ndarray] = []
            if is_video:
                cap = cv2.VideoCapture(args.image_path)
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    raw_frames.append(frame)
                cap.release()
            else:
                # TODO: Fully implement offline rendering for GIFs
                logger.log("Offline rendering for images/GIFs not yet fully implemented.")
                if img:
                    frame_rgba = img.convert("RGBA")
                    # Worker expects BGR, so convert from PIL's RGBA
                    raw_frames.append(cv2.cvtColor(np.array(frame_rgba), cv2.COLOR_RGBA2BGR))

            n_frames = len(raw_frames)
            logger.log(f"Loaded {n_frames} raw frames for processing.")

            # Create a task for each frame
            tasks = [(frame, args, t_pixel_w, t_pixel_h, "\033[0m") for frame in raw_frames]
            
            num_workers = max(1, cpu_count() - 1)
            logger.log(f"Starting multiprocessing pool with {num_workers} workers.")
            
            with Pool(processes=num_workers) as pool:
                ansi_frames = pool.map(render_frame_for_offline, tasks)
            
            logger.log("All frames rendered to ANSI strings.")

            fps = (1 / durations[0]) if durations else 30.0
            metadata = {
               "version": 1,
               "rows": t_char_h,
               "cols": t_char_w,
               "color_depth": 24,
               "frame_count": n_frames,
               "fps": fps,
               "durations": durations if durations else [1/fps] * n_frames,
               "loop": args.loop
            }
            
            metadata_str = json.dumps(metadata, separators=(',', ':'))
            metadata_bytes = metadata_str.encode('utf-8')

            with open(args.output, 'wb') as f:
                f.write(b'ANSIPIX\x00')
                f.write(struct.pack('<I', 1))
                f.write(struct.pack('<I', len(metadata_bytes)))
                f.write(metadata_bytes)
                
                stripped_frames = [frame.strip() for frame in ansi_frames]
                full_frame_data = "\n".join(stripped_frames).encode('utf-8')
                f.write(full_frame_data)

            logger.log(f"Successfully saved to {args.output}")
            return

        # --- Live Playback Logic ---
        if is_video:
            exit_event = Event()
            def signal_handler(sig: int, frame: Optional[object]) -> None:
                exit_event.set()
            
            original_sigint = signal.getsignal(signal.SIGINT)
            original_sigterm = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            args.background = None
            
            _t_char_w, _t_char_h, target_pixel_w, target_pixel_h = calculate_dimensions(
                orig_w, orig_h, term_w, effective_h
            )
            
            play_video(
                args, args.image_path, target_pixel_w, target_pixel_h,
                term_w, effective_h * 2,
                n_frames_from_loader, durations,
                logger, exit_event
            )
            
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
        else:
            play_image_animation(args, args.image_path, logger)

if __name__ == "__main__":
    epilog_text = "Authored by EdgeOfAssembly (2025-10-07)"
    parser = argparse.ArgumentParser(
        description="Render an image, animated GIF, or video in the terminal.",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("image_path", help="Path to the input image, GIF, video, or .ansipix file.")
    # TODO: Implement --width, --height, and --full-width arguments
    parser.add_argument("--width", type=int, help="NOT IMPLEMENTED: Optional target terminal width in characters.")
    parser.add_argument("--height", type=int, help="NOT IMPLEMENTED: Optional target terminal height in lines.")
    parser.add_argument("--full-width", action="store_true", help="NOT IMPLEMENTED: Use full terminal width.")
    
    parser.add_argument("-o", "--output", help="Optional output file path. Saves to a standard text file or a custom .ansipix file.")
    parser.add_argument("--loop", type=int, default=0, help="Number of times to loop the animation (0 for infinite).")
    parser.add_argument("--debug", help="Save debug output to the specified file.")
    parser.add_argument("--background", help="For images: solid color (name or hex) or image path.")
    parser.add_argument("--tile", action="store_true", help="For background images: tile instead of stretching.")
    parser.add_argument("--buffer-percent", type=int, default=10, help="Video pre-buffering RAM percentage (0-100).")
    parser.add_argument("--downsample-method", choices=['nearest', 'linear', 'cubic', 'area', 'lanczos4'], default='area', help="Downsampling method for resizing.")
    parser.add_argument("--profile", help="Profile the execution and save results to the specified file.")
    args = parser.parse_args()

    if args.profile:
        import cProfile, pstats
        profiler = cProfile.Profile()
        profiler.enable()
        main(args)
        profiler.disable()
        stats = pstats.Stats(profiler)
        with open(args.profile, 'w') as f:
            stats.stream = f
            stats.sort_stats('cumulative').print_stats()
    else:
        main(args)
