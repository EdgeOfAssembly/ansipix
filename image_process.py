"""
image_process.py - Frame Processing Utilities

This module contains functions for processing individual media frames. The primary
function, `process_single_frame`, is used in the video playback pipeline to handle
the resizing and color space conversion required before a frame can be rendered.
"""
import cv2
import argparse
import numpy as np
from typing import Dict, Any

def process_single_frame(
    frame: np.ndarray, 
    args: argparse.Namespace, 
    target_width: int, 
    target_height: int, 
    is_video: bool = False
) -> np.ndarray:
    """
    Processes a single frame, primarily for the video pipeline.

    This involves two main steps:
    1. Resizing the frame to the calculated target pixel dimensions.
    2. Converting the color space from OpenCV's default BGR to RGBA, which is
       expected by the rendering function.

    Args:
        frame (np.ndarray): The input frame as a NumPy array (typically BGR).
        args (argparse.Namespace): Command-line arguments to get the downsample method.
        target_width (int): The target width in pixels.
        target_height (int): The target height in pixels.
        is_video (bool): A flag indicating if the frame is from a video.

    Returns:
        np.ndarray: The processed frame in RGBA format.
    """
    if is_video:
        method_map: Dict[str, int] = {
            'nearest': cv2.INTER_NEAREST,
            'linear': cv2.INTER_LINEAR,
            'cubic': cv2.INTER_CUBIC,
            'area': cv2.INTER_AREA,
            'lanczos4': cv2.INTER_LANCZOS4
        }
        interpolation_method = method_map.get(args.downsample_method, cv2.INTER_AREA)
        
        resized = cv2.resize(frame, (target_width, target_height), interpolation=interpolation_method)
        
        return cv2.cvtColor(resized, cv2.COLOR_BGR2RGBA)
    
    # This path is not currently used for video but kept for potential future use.
    return frame