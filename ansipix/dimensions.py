"""
dimensions.py - Rendering Dimension Calculation

This module provides the single source of truth for calculating the correct
rendering dimensions for any media file to fit within the terminal while
preserving its aspect ratio. It accounts for the non-square nature of terminal
character cells to prevent visual distortion.
"""
from typing import Tuple

# A terminal character cell is roughly twice as tall as it is wide.
# We render two vertical pixels per character cell using the '▀' character.
_PIXEL_PER_CHAR_W = 1
_PIXEL_PER_CHAR_H = 2

def calculate_dimensions(orig_w: int, orig_h: int, term_w: int, term_h: int) -> Tuple[int, int, int, int]:
    """
    Computes rendering dimensions to fit media correctly in the terminal.

    Args:
        orig_w: Original width of the media in pixels.
        orig_h: Original height of the media in pixels.
        term_w: Terminal width in characters.
        term_h: Terminal height in characters.

    Returns:
        A tuple containing:
        - target_char_w: The calculated width in terminal characters.
        - target_char_h: The calculated height in terminal characters.
        - target_pixel_w: The calculated width in pixels for resizing.
        - target_pixel_h: The calculated height in pixels for resizing.
    """
    # Aspect ratio of a character cell, assuming a standard 2:1 font height:width ratio.
    char_aspect_ratio = 0.5
    img_aspect_ratio = orig_w / orig_h if orig_h > 0 else 1.0
    
    # Calculate potential dimensions based on fitting to terminal width
    w_fit_w = term_w
    w_fit_h = round(term_w / (img_aspect_ratio / char_aspect_ratio)) if img_aspect_ratio > 0 else term_h
    
    # Calculate potential dimensions based on fitting to terminal height
    h_fit_h = term_h
    h_fit_w = round(term_h * (img_aspect_ratio / char_aspect_ratio))

    # Choose the smaller of the two fits to ensure the media is fully visible
    if w_fit_w <= term_w and w_fit_h <= term_h:
        target_char_w, target_char_h = w_fit_w, w_fit_h
    else:
        target_char_w, target_char_h = h_fit_w, h_fit_h

    # Convert final character dimensions back to pixel dimensions for the renderer
    target_pixel_w = target_char_w * _PIXEL_PER_CHAR_W
    target_pixel_h = target_char_h * _PIXEL_PER_CHAR_H
    
    return target_char_w, target_char_h, target_pixel_w, target_pixel_h