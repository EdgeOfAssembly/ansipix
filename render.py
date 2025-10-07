"""
render.py - High-Performance ANSI Rendering

This module contains the performance-critical function for converting a processed
pixel buffer (NumPy array) into an ANSI escape code string. This implementation
has been proven by profiling to be the most efficient version, outperforming
more complex vectorized or string-building approaches. Its speed comes from its
simplicity and directness, minimizing Python overhead.
"""
import numpy as np
import cv2
from typing import List

def render_video_image(img: np.ndarray, target_width: int, target_height: int, reset: str) -> List[str]:
    """
    Renders a NumPy array (frame) into a list of ANSI-formatted strings.

    This function uses the "upper block" character '▀' to represent two pixels
    vertically in a single character cell. The foreground color of the character
    sets the top pixel, and the background color sets the bottom pixel.

    This implementation is highly optimized:
    - It only sends an ANSI color code when the foreground or background color changes
      from the previous pixel, minimizing the number of bytes sent to the terminal.
    - It builds each line as a list of parts and joins them once, which is more
      efficient than repeated string concatenation.

    Args:
        img (np.ndarray): The input image as a NumPy array in RGBA format.
        target_width (int): The target width in characters (and pixels).
        target_height (int): The target height in pixels (must be an even number).
        reset (str): The ANSI reset string to append at the end of each line.

    Returns:
        List[str]: A list of strings, where each string is a fully rendered row of
                   the ANSI art, including a newline character.
    """
    # This function is the fastest version as determined by profiling.
    # The direct, nested loop approach minimizes Python overhead compared to
    # more complex vectorized or list comprehension methods for this specific task.
    # The true bottleneck is f-string generation and terminal I/O, which this
    # simple structure handles most efficiently.
    
    # Extract all top and bottom pixel rows at once for efficiency
    top_rows = img[0::2, :target_width]
    bot_rows = img[1::2, :target_width]
    
    lines: List[str] = []
    num_rows = top_rows.shape[0]
    upper_block = "▀"
    
    for row in range(num_rows):
        parts: List[str] = []
        current_fg: Tuple[int, int, int] = (-1, -1, -1)
        current_bg: Tuple[int, int, int] = (-1, -1, -1)

        for col in range(target_width):
            # Direct tuple creation is faster than repeated slicing
            fg = (top_rows[row, col, 0], top_rows[row, col, 1], top_rows[row, col, 2])
            bg = (bot_rows[row, col, 0], bot_rows[row, col, 1], bot_rows[row, col, 2])
            
            # Critical Optimization: Only change color when necessary
            if fg != current_fg or bg != current_bg:
                fg_esc = f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m"
                bg_esc = f"\033[48;2;{bg[0]};{bg[1]};{bg[2]}m"
                parts.extend([bg_esc, fg_esc])
                current_fg, current_bg = fg, bg
                
            parts.append(upper_block)
        
        parts.append(reset + '\n')
        lines.append(''.join(parts))
    
    return lines