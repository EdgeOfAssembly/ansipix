"""
offline_renderer.py - Multiprocessing Worker

This module defines the worker function used by the multiprocessing pool for the
high-performance offline creation of .ansipix files. By isolating this function,
we keep the main application logic clean and ensure proper behavior for `multiprocessing`.
"""
import numpy as np
import argparse
from typing import Tuple

from render import render_video_image
from image_process import process_single_frame

def render_frame_for_offline(task_args: Tuple[np.ndarray, argparse.Namespace, int, int, str]) -> str:
    """
    Worker function executed by each process in the multiprocessing pool.

    It takes a single raw video frame and all necessary rendering arguments,
    processes it, converts it to an ANSI string, and returns the result.

    Args:
        task_args (Tuple): A tuple containing all arguments needed for rendering:
            - frame (np.ndarray): The raw BGR frame from OpenCV.
            - args (argparse.Namespace): The application's command-line arguments.
            - target_pixel_w (int): The target width in pixels for resizing.
            - target_pixel_h (int): The target height in pixels for resizing.
            - reset_char (str): The ANSI reset character string.

    Returns:
        str: The fully rendered ANSI art for the single frame.
    """
    frame, args, target_pixel_w, target_pixel_h, reset_char = task_args

    # 1. Process the frame (resize, color convert)
    processed_frame = process_single_frame(frame, args, target_pixel_w, target_pixel_h, is_video=True)
    
    # 2. Render to ANSI string (using the fast V1 renderer)
    lines = render_video_image(processed_frame, target_pixel_w, target_pixel_h, reset_char)
    
    # Return a single string for the whole frame.
    return "".join(lines)