"""
media_loader.py - Media Information and Loading

This module provides a single function, `load_media`, which acts as a unified
interface for inspecting different media files (videos, images, GIFs). It
determoses the media type, extracts critical metadata like dimensions, frame counts,
and durations, and logs this information. It does not load all frame data into
memory, making it efficient for large files.
"""
import cv2
from PIL import Image, ImageSequence
from typing import Tuple, List, Optional
from .debug_logger import DebugLogger

def load_media(image_path: str, logger: DebugLogger) -> Tuple[bool, List, List[float], int, Optional[Image.Image], int, int]:
    """
    Inspects a media file and loads its essential metadata.

    This function checks if the file is a video or an image/GIF based on its
    extension. It then uses OpenCV or Pillow to extract dimensions, frame count,
    FPS, and frame durations without loading the entire file into memory.

    Args:
        image_path (str): Path to the input media file.
        logger (DebugLogger): The logger instance for debug output.

    Returns:
        A tuple containing:
        - is_video (bool): True if the media is a video, False otherwise.
        - frames (List): An empty list, kept for legacy reasons.
        - durations (List[float]): A list of frame durations in seconds. For videos,
          this is calculated from FPS. For GIFs, it's read from the file.
        - n_frames (int): The total number of frames.
        - img (Optional[Image.Image]): A Pillow Image object if the media is an
          image/GIF, otherwise None.
        - orig_w (int): The original width of the media in pixels.
        - orig_h (int): The original height of the media in pixels.
    """
    # TODO: Implement more robust media type detection (e.g., by content, not just extension)
    is_video = image_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv'))
    frames: List = []
    durations: List[float] = []
    n_frames: int = 0
    img: Optional[Image.Image] = None
    orig_w: int = 0
    orig_h: int = 0

    try:
        if is_video:
            cap = cv2.VideoCapture(image_path)
            if not cap.isOpened(): raise IOError("Cannot open video file")
            orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_duration = 1 / fps if fps > 0 else 0.04
            n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            durations = [frame_duration] * n_frames
            
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            total_duration = n_frames / fps if fps > 0 else 0
            cap.release()

            logger.log(f"--- Media Info ---\nMedia Type: Video\nVideo size: {orig_w}x{orig_h}px, FPS: {fps:.2f}, Frames: {n_frames}")
            logger.log(f"Video codec: {fourcc_str}, duration: {total_duration:.2f}s\n------------------")
        else:
            img = Image.open(image_path)
            orig_w, orig_h = img.size
            is_animated = hasattr(img, 'n_frames') and img.n_frames > 1
            
            logger.log(f"--- Media Info ---\nMedia Type: Image\nOriginal image size: {orig_w}x{orig_h}px")
            logger.log(f"Image format: {img.format}, mode: {img.mode}, animated: {is_animated}\n------------------")

            if is_animated:
                durations = [frame.info.get('duration', 100) / 1000.0 for frame in ImageSequence.Iterator(img)]
                n_frames = len(durations)
                if n_frames > 0:
                    avg_duration = sum(durations) / n_frames if n_frames > 0 else 0
                    logger.log(f"GIF frames: {n_frames}, average duration: {avg_duration:.3f}s/frame")
            else:
                n_frames = 1
                durations = [0.0]
                img = img.convert("RGBA")

    except Exception as e:
        raise IOError(f"Error loading media '{image_path}': {e}") from e
    
    return is_video, frames, durations, n_frames, img, orig_w, orig_h
