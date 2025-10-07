"""
ansipix/cli.py - Main Entry Point and CLI Logic
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

# Use relative imports within the package
from .media_loader import load_media
from .animation_player import play_video, play_ansipix_file
from .dimensions import calculate_dimensions
from .image_player import play_image_animation
from .term_utils import get_current_font
from .debug_logger import DebugLogger

def main_logic(args: argparse.Namespace) -> None:
    """Main controller function for the ansipix application."""
    if args.image_path.lower().endswith('.ansipix'):
        play_ansipix_file(args.image_path, args)
        return

    with DebugLogger(args.debug) as logger:
        # The rest of your main application logic goes here...
        # (This is the code that was previously in the if __name__ == "__main__" block)
        try:
            term_w, term_h = shutil.get_terminal_size()
        except OSError:
            term_w, term_h = 80, 24
        effective_h = max(1, term_h - 1)

        if logger.is_active:
            font_family, font_w, font_h = get_current_font()
            pixel_w, pixel_h = term_w * font_w, effective_h * font_h
            logger.log(f"--- Terminal & System Info ---\nTerminal size: {term_w}x{term_h} chars")
            if font_w > 0 and font_h > 0:
                logger.log(f"Detected font: '{font_family}' ({font_w}x{font_h}px/char)")
            logger.log("--------------------------------\n")

        is_video, _, durations, n_frames_loader, img, orig_w, orig_h = load_media(args.image_path, logger)
        
        if args.output and args.output.lower().endswith('.ansipix'):
            from multiprocessing import Pool, cpu_count
            from .offline_renderer import render_frame_for_offline
            
            logger.log("Offline rendering to .ansipix format initiated.")
            t_char_w, t_char_h, t_pixel_w, t_pixel_h = calculate_dimensions(orig_w, orig_h, term_w, effective_h)
            
            raw_frames: list = []
            if is_video:
                import cv2
                cap = cv2.VideoCapture(args.image_path)
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    raw_frames.append(frame)
                cap.release()
            else:
                if img:
                    import numpy as np
                    import cv2
                    # This part needs to handle GIF frames properly
                    # For now, let's assume single image for simplicity of the fix
                    raw_frames.append(cv2.cvtColor(np.array(img.convert("RGBA")), cv2.COLOR_RGBA2BGR))

            n_frames = len(raw_frames)
            tasks = [(frame, args, t_pixel_w, t_pixel_h, "\033[0m") for frame in raw_frames]
            
            with Pool(processes=max(1, cpu_count() - 1)) as pool:
                ansi_frames = pool.map(render_frame_for_offline, tasks)
            
            fps = (1 / durations[0]) if durations else 30.0
            metadata = { "version": 1, "rows": t_char_h, "cols": t_char_w, "color_depth": 24, "frame_count": n_frames, "fps": fps, "durations": durations or [1/fps] * n_frames, "loop": args.loop }
            metadata_bytes = json.dumps(metadata, separators=(',', ':')).encode('utf-8')

            with open(args.output, 'wb') as f:
                f.write(b'ANSIPIX\x00')
                f.write(struct.pack('<I', 1))
                f.write(struct.pack('<I', len(metadata_bytes)))
                f.write(metadata_bytes)
                f.write("\n".join(frame.strip() for frame in ansi_frames).encode('utf-8'))

            logger.log(f"Successfully saved to {args.output}")
            return

        if is_video:
            exit_event = Event()
            def signal_handler(sig: int, frame: Optional[object]) -> None: exit_event.set()
            
            original_sigint, original_sigterm = signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            _t_char_w, _t_char_h, target_pixel_w, target_pixel_h = calculate_dimensions(orig_w, orig_h, term_w, effective_h)
            play_video(args, args.image_path, target_pixel_w, target_pixel_h, term_w, effective_h * 2, n_frames_loader, durations, logger, exit_event)
            
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
        else:
            play_image_animation(args, args.image_path, logger)


def cli():
    """The command-line interface entry point."""
    if os.name == 'nt': os.system('')
    
    parser = argparse.ArgumentParser(description="Render an image, animated GIF, or video in the terminal.", epilog="Authored by EdgeOfAssembly", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image_path", help="Path to the input image, GIF, video, or .ansipix file.")
    parser.add_argument("--width", type=int, help="NOT IMPLEMENTED: Optional target terminal width.")
    parser.add_argument("--height", type=int, help="NOT IMPLEMENTED: Optional target terminal height.")
    parser.add_argument("-o", "--output", help="Optional output file path for .ansipix creation.")
    parser.add_argument("--loop", type=int, default=0, help="Number of times to loop animation (0 for infinite).")
    parser.add_argument("--debug", help="Save debug output to the specified file.")
    parser.add_argument("--background", help="For images: solid color (name or hex) or image path.")
    parser.add_argument("--tile", action="store_true", help="For background images: tile instead of stretching.")
    parser.add_argument("--full-width", action="store_true", help="NOT IMPLEMENTED: Use full terminal width.")
    parser.add_argument("--buffer-percent", type=int, default=10, help="Video pre-buffering RAM percentage.")
    parser.add_argument("--downsample-method", choices=['nearest', 'linear', 'cubic', 'area', 'lanczos4'], default='area', help="Downsampling method for resizing.")
    parser.add_argument("--profile", help="Profile execution and save results to file.")
    args = parser.parse_args()

    if args.profile:
        import cProfile, pstats
        profiler = cProfile.Profile()
        profiler.enable()
        main_logic(args)
        profiler.disable()
        stats = pstats.Stats(profiler)
        with open(args.profile, 'w') as f:
            stats.stream = f
            stats.sort_stats('cumulative').print_stats()
    else:
        main_logic(args)