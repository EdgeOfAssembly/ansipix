"""
animation_player.py - Media Playback Handlers

This module contains the functions responsible for playing back animations in the terminal.
It provides two main functionalities:
1.  `play_video`: A high-performance, real-time renderer for video files. It uses a
    producer-consumer model with threads to decouple video decoding from terminal
    rendering, ensuring smooth playback.
2.  `play_ansipix_file`: A highly efficient player for the custom .ansipix format.
    It reads pre-rendered frames and their metadata, then plays them back with the
    correct timing, resulting in very low CPU usage.
"""
import time
import cv2
from queue import Queue, Empty
from threading import Thread, Event
import gc
import os
import sys
import argparse
import struct
import json
import signal
from typing import Tuple, List, Optional

from render import render_video_image
from image_process import process_single_frame
from debug_logger import DebugLogger

def producer(
    queue: Queue, 
    args: argparse.Namespace, 
    image_path: str, 
    target_width: int, 
    target_height: int, 
    loop: int, 
    stop_event: Event, 
    logger: DebugLogger
) -> None:
    """
    A producer thread that decodes video frames and puts them into a queue.

    This runs in a separate thread to prevent the main rendering loop from blocking
    while waiting for the next frame to be decoded from the video file.

    Args:
        queue (Queue): The thread-safe queue to put processed frames into.
        args (argparse.Namespace): Command-line arguments.
        image_path (str): Path to the video file.
        target_width (int): The target pixel width for resizing frames.
        target_height (int): The target pixel height for resizing frames.
        loop (int): The number of times to loop the video.
        stop_event (Event): An event to signal when the thread should stop.
        logger (DebugLogger): The logger instance for debug output.
    """
    source: Optional[cv2.VideoCapture] = None
    try:
        source = cv2.VideoCapture(image_path)
        if not source.isOpened():
            raise IOError(f"Cannot open video file: {image_path}")

        current_loop = 0
        while (loop == 0 or current_loop < loop) and not stop_event.is_set():
            n_frames = int(source.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = source.get(cv2.CAP_PROP_FPS)
            duration = 1 / fps if fps > 0 else 0.04

            for _ in range(n_frames):
                if stop_event.is_set(): break
                ret, frame = source.read()
                if not ret: break
                
                processed = process_single_frame(frame, args, target_width, target_height, is_video=True)
                queue.put((processed, duration))
            
            source.set(cv2.CAP_PROP_POS_FRAMES, 0) # Rewind video for looping
            current_loop += 1
    
    except Exception as e:
        logger.log(f"Error in producer thread: {e}")
    finally:
        if source:
            source.release()
        queue.put(None) # Sentinel value to signal the end of the stream

def play_video(
    args: argparse.Namespace, 
    image_path: str, 
    target_width: int, 
    target_height: int, 
    render_width: int, 
    render_height: int, 
    n_frames: int, 
    durations: List[float], 
    logger: DebugLogger, 
    exit_event: Event
) -> None:
    """
    Plays a video file by rendering it live in the terminal.

    Uses a producer-consumer model to ensure smooth playback. The main loop (consumer)
    retrieves frames from a queue and renders them, while a separate thread (producer)
    decodes frames and fills the queue.

    Args:
        args (argparse.Namespace): Command-line arguments.
        image_path (str): Path to the video file.
        target_width (int): Pixel width for resizing.
        target_height (int): Pixel height for resizing.
        render_width (int): Character width of the terminal.
        render_height (int): Character height of the terminal.
        n_frames (int): Total number of frames in the video.
        durations (List[float]): List of durations for each frame.
        logger (DebugLogger): Logger for debug output.
        exit_event (Event): Event to signal for graceful termination.
    """
    logger.log("Video playback started. Using on-demand producer/consumer model.")

    hide_cursor, show_cursor = "\033[?25l", "\033[?25h"
    alt_buffer_enter, alt_buffer_exit = "\033[?1049h", "\033[?1049l"
    clear_screen, reset = "\033[2J\033[H", "\033[0m"
    
    sys.stdout.write(alt_buffer_enter + hide_cursor + clear_screen)
    sys.stdout.flush()
    gc.disable() # Disable garbage collection during playback for performance

    frame_queue: Queue = Queue(maxsize=50)
    producer_thread = Thread(target=producer, args=(frame_queue, args, image_path, target_width, target_height, args.loop, exit_event, logger))
    producer_thread.start()

    total_frames_played = 0
    while not exit_event.is_set():
        try:
            item = frame_queue.get(timeout=0.01)
            if item is None: break # End of stream
            
            processed_frame, duration = item
            start_time = time.perf_counter()
            
            lines = render_video_image(processed_frame, target_width, target_height, reset)
            output_str = ''.join(lines)
            sys.stdout.write("\033[H" + output_str)
            sys.stdout.flush()
            
            write_time = time.perf_counter() - start_time
            total_frames_played += 1
            if logger.is_active and n_frames > 0:
                current_frame_in_loop = (total_frames_played - 1) % n_frames + 1
                logger.log(f"Frame {current_frame_in_loop}/{n_frames} write time: {write_time*1000:.1f}ms")
            
            time.sleep(max(0, duration - write_time))
        except Empty:
            continue
    
    producer_thread.join(timeout=1.0)
    if producer_thread.is_alive(): os._exit(0) # Force exit if thread is stuck
    
    gc.enable() # Re-enable garbage collection
    sys.stdout.write(show_cursor + alt_buffer_exit + "\n")
    sys.stdout.flush()
    logger.log("Video playback finished. Exited alternate buffer.")

def play_ansipix_file(file_path: str, args: argparse.Namespace) -> None:
    """
    Loads and plays a pre-rendered .ansipix file.

    This function reads the header and metadata, reconstructs the frames, and then
    plays them back in the terminal with the correct timing. It is highly efficient
    as no real-time rendering is required.

    Args:
        file_path (str): The path to the .ansipix file.
        args (argparse.Namespace): The parsed command-line arguments, used for loop control.
    """
    hide_cursor, show_cursor = "\033[?25l", "\033[?25h"
    alt_buffer_enter, alt_buffer_exit = "\033[?1049h", "\033[?1049l"
    clear_screen = "\033[2J\033[H"
    
    exit_event = Event()
    def signal_handler(sig: int, frame: Optional[object]) -> None:
        exit_event.set()
    
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        with open(file_path, 'rb') as f:
            if f.read(8) != b'ANSIPIX\x00':
                raise ValueError("Not a valid .ansipix file (magic string mismatch).")
            
            version = struct.unpack('<I', f.read(4))[0]
            if version > 1:
                print(f"Warning: .ansipix file is v{version}, player supports v1.", file=sys.stderr)

            metadata_len = struct.unpack('<I', f.read(4))[0]
            metadata_bytes = f.read(metadata_len)
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            
            all_lines = f.read().decode('utf-8').split('\n')
            rows_per_frame = metadata.get('rows', 1)
            
            frames = []
            for i in range(0, len(all_lines), rows_per_frame):
                frame_lines = all_lines[i:i + rows_per_frame]
                frames.append("\n".join(frame_lines))

            if frames and not frames[-1].strip():
                frames.pop()

            if len(frames) != metadata.get('frame_count', 0):
                print(f"Warning: Frame count mismatch. Metadata: {metadata.get('frame_count')}, Found: {len(frames)}", file=sys.stderr)

        sys.stdout.write(alt_buffer_enter + hide_cursor + clear_screen)
        sys.stdout.flush()

        loop_count = 0
        # Use loop count from args if provided, otherwise from metadata
        max_loops = args.loop if args.loop != 0 else metadata.get('loop', 0)
        durations = metadata.get('durations', [0.04])
        
        while not exit_event.is_set():
            for i, frame in enumerate(frames):
                if exit_event.is_set(): break
                
                start_time = time.perf_counter()
                
                sys.stdout.write("\033[H" + frame)
                sys.stdout.flush()
                
                write_time = time.perf_counter() - start_time
                duration = durations[i] if i < len(durations) else durations[-1]
                time.sleep(max(0, duration - write_time))

            loop_count += 1
            if max_loops > 0 and loop_count >= max_loops: break
            if max_loops == 0 and len(frames) > 1: continue
            else: break

    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"Error playing .ansipix file: {e}", file=sys.stderr)
    finally:
        sys.stdout.write(show_cursor + alt_buffer_exit + "\n")
        sys.stdout.flush()
        signal.signal(signal.SIGINT, original_sigint)