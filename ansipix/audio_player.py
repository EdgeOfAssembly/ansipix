"""
audio_player.py - Audio Playback Handler

This module provides low-latency audio playback functionality for video files.
It uses the miniaudio library which supports multiple audio formats (WAV, MP3, FLAC, etc.)
and provides very low latency playback.
"""
import os
import subprocess
import tempfile
from threading import Thread, Event
from typing import Optional
from .debug_logger import DebugLogger

try:
    import miniaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class AudioPlayer:
    """
    A low-latency audio player for video files.
    
    Extracts audio from video files and plays it in sync with video playback.
    Uses a separate thread to avoid blocking the main video rendering loop.
    """
    
    def __init__(self, video_path: str, logger: DebugLogger):
        """
        Initialize the audio player.
        
        Args:
            video_path (str): Path to the video file.
            logger (DebugLogger): Logger for debug output.
        """
        self.video_path = video_path
        self.logger = logger
        self.audio_file: Optional[str] = None
        self.device: Optional[miniaudio.PlaybackDevice] = None
        self.stream: Optional[miniaudio.StreamableSource] = None
        self.thread: Optional[Thread] = None
        self.stop_event = Event()
        self.audio_available = AUDIO_AVAILABLE
        
        if not AUDIO_AVAILABLE:
            self.logger.log("Warning: miniaudio not available. Audio playback disabled.")
    
    def _extract_audio(self) -> Optional[str]:
        """
        Extract audio from video file to a temporary WAV file.
        
        Returns:
            Optional[str]: Path to the extracted audio file, or None if extraction failed.
        """
        if not self.audio_available:
            return None
        
        # Create a temporary file for the audio
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='ansipix_audio_')
        os.close(temp_fd)
        
        try:
            # Use OpenCV to extract audio - check if video has audio first
            import cv2
            cap = cv2.VideoCapture(self.video_path)
            # OpenCV doesn't provide direct audio access, so we'll use subprocess with ffmpeg if available
            cap.release()
            
            # Try to use ffmpeg to extract audio
            try:
                result = subprocess.run(
                    ['ffmpeg', '-i', self.video_path, '-vn', '-acodec', 'pcm_s16le', 
                     '-ar', '44100', '-ac', '2', '-y', temp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10
                )
                
                if result.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    self.logger.log(f"Audio extracted successfully to {temp_path}")
                    return temp_path
                else:
                    self.logger.log("Audio extraction failed or video has no audio stream")
                    os.unlink(temp_path)
                    return None
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
                self.logger.log(f"Could not extract audio: {e}")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None
                
        except Exception as e:
            self.logger.log(f"Error during audio extraction: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    
    def _playback_loop(self):
        """
        The audio playback loop running in a separate thread.
        Streams audio data to the playback device.
        """
        if not self.audio_file or not self.audio_available:
            return
        
        try:
            # Load the audio file to get properties
            decoded = miniaudio.wav_read_file_f32(self.audio_file)
            
            # Create playback device
            self.device = miniaudio.PlaybackDevice(
                sample_rate=decoded.sample_rate,
                nchannels=decoded.nchannels,
                output_format=miniaudio.SampleFormat.FLOAT32
            )
            
            self.logger.log(f"Audio playback started: {decoded.sample_rate}Hz, {decoded.nchannels} channels")
            
            # Create streaming generator
            self.stream = miniaudio.stream_file(
                self.audio_file,
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=decoded.nchannels,
                sample_rate=decoded.sample_rate
            )
            
            # Start playback
            self.device.start(self.stream)
            
            # Keep thread alive while playing
            while not self.stop_event.is_set() and self.device:
                self.stop_event.wait(0.1)
            
        except Exception as e:
            self.logger.log(f"Error during audio playback: {e}")
        finally:
            self._cleanup()
    
    def start(self) -> bool:
        """
        Start audio playback in a separate thread.
        
        Returns:
            bool: True if audio playback started successfully, False otherwise.
        """
        if not self.audio_available:
            return False
        
        # Extract audio from video
        self.audio_file = self._extract_audio()
        if not self.audio_file:
            self.logger.log("No audio to play")
            return False
        
        # Start playback thread
        self.thread = Thread(target=self._playback_loop, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """
        Stop audio playback and cleanup resources.
        """
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        self._cleanup()
    
    def _cleanup(self):
        """
        Cleanup audio resources and temporary files.
        """
        try:
            if self.device:
                self.device.close()
                self.device = None
            
            if self.stream:
                self.stream = None
            
            if self.audio_file and os.path.exists(self.audio_file):
                try:
                    os.unlink(self.audio_file)
                    self.logger.log(f"Cleaned up temporary audio file: {self.audio_file}")
                except Exception as e:
                    self.logger.log(f"Could not delete temporary audio file: {e}")
                self.audio_file = None
        except Exception as e:
            self.logger.log(f"Error during cleanup: {e}")
