"""
audio_player.py - Audio Playback Handler

This module provides low-latency audio playback functionality for video files.
It uses the miniaudio library which supports multiple audio formats (WAV, MP3, FLAC, etc.)
and provides very low latency playback.
"""
import os
import subprocess
import json
from threading import Thread, Event
from typing import Optional
import platform
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
        self.proc: Optional[subprocess.Popen] = None
        self.device: Optional[miniaudio.PlaybackDevice] = None
        self.thread: Optional[Thread] = None
        self.stop_event = Event()
        self.audio_available = AUDIO_AVAILABLE
        self.audio_channels = 2
        self.audio_sample_rate = 44100
        self.has_audio = False
        self._alsa_device = None  # Will hold detected device (e.g., 'pipewire' or 'plughw:0,0')
        
        if not AUDIO_AVAILABLE:
            self.logger.log("Warning: miniaudio not available. Audio playback disabled.")
        
        # Auto-detect and configure ALSA backend
        self._auto_configure_alsa()
    
    def _auto_configure_alsa(self):
        """Detect PipeWire or other shared audio servers and set ALSA device accordingly."""
        if platform.system() != 'Linux':
            self.logger.log("DEBUG: Non-Linux platform—skipping ALSA auto-config")
            return
        
        self.logger.log("DEBUG: Auto-configuring ALSA backend...")
        
        # Check for PipeWire (most common shared server)
        try:
            result = subprocess.run(['pgrep', '-f', 'pipewire'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                self.logger.log("DEBUG: PipeWire detected—setting ALSA_PCM_DEVICE=pipewire for shared access")
                os.environ['ALSA_PCM_DEVICE'] = 'pipewire'
                self._alsa_device = 'pipewire'
                return
        except (FileNotFoundError, Exception) as e:
            self.logger.log(f"DEBUG: PipeWire check failed: {e}")
        
        # Fallback: Try direct ALSA (analog, assuming Card 0 Dev 0)
        self.logger.log("DEBUG: No PipeWire—defaulting to direct ALSA (plughw:0,0)")
        os.environ['ALSA_PCM_DEVICE'] = 'plughw:0,0'
        self._alsa_device = 'plughw:0,0'
    
    def _detect_audio_params(self) -> bool:
        """Detect audio stream params using ffprobe."""
        self.logger.log("DEBUG: Entering _detect_audio_params")
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams',
                '-select_streams', 'a:0', self.video_path
            ]
            self.logger.log(f"DEBUG: Running ffprobe: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.log(f"DEBUG: ffprobe stdout: {result.stdout[:200]}...")  # Truncate for log
            info = json.loads(result.stdout)
            if info['streams']:
                stream = info['streams'][0]
                self.has_audio = True
                self.audio_channels = int(stream.get('channels', 2))
                self.audio_sample_rate = int(stream.get('sample_rate', 44100))
                self.logger.log(f"ffprobe: {self.audio_channels}ch @ {self.audio_sample_rate}Hz, codec: {stream.get('codec_name', 'unknown')}")
                return True
            else:
                self.logger.log("DEBUG: No audio streams found in ffprobe")
                return False
        except subprocess.CalledProcessError as e:
            self.logger.log(f"ffprobe subprocess error: {e}, stdout: {e.stdout}, stderr: {e.stderr}")
            return False
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            self.logger.log(f"ffprobe failed: {e}")
            return False
    
    def _start_ffmpeg(self) -> bool:
        """Launch FFmpeg to pipe raw PCM from video."""
        self.logger.log("DEBUG: Entering _start_ffmpeg")
        try:
            self.logger.log(f"DEBUG: Launching FFmpeg with params: {self.audio_channels}ch @ {self.audio_sample_rate}Hz")
            self.proc = subprocess.Popen([
                'ffmpeg', '-v', 'quiet', '-nostdin',
                '-i', self.video_path,
                '-f', 's16le',
                '-acodec', 'pcm_s16le',
                '-ac', str(self.audio_channels),
                '-ar', str(self.audio_sample_rate),
                '-'
            ], stdout=subprocess.PIPE, bufsize=0, stderr=subprocess.DEVNULL)

            self.logger.log(f"DEBUG: FFmpeg PID: {self.proc.pid}, poll(): {self.proc.poll()}")

            if self.proc.poll() is not None:
                self.logger.log(f"FFmpeg failed immediately: {self.proc.returncode}")
                return False

            # Test read
            test_chunk = self.proc.stdout.read(1024)
            self.logger.log(f"FFmpeg test read: {len(test_chunk)} bytes, first 20: {test_chunk[:20]}")
            if all(b == 0 for b in test_chunk):
                self.logger.log("DEBUG: Test chunk all zeros (expected if audio delayed)")
            return True
        except FileNotFoundError:
            self.logger.log("FFmpeg not found")
            return False
        except Exception as e:
            self.logger.log(f"FFmpeg error: {e}")
            import traceback
            self.logger.log(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _playback_loop(self):
        """
        The audio playback loop running in a separate thread.
        Streams audio data to the playback device.
        """
        self.logger.log("DEBUG: Entering _playback_loop")
        if not self.audio_available:
            self.logger.log("DEBUG: Audio not available - exiting loop")
            return
        
        try:
            if not self._detect_audio_params():
                self.logger.log("No audio stream detected - exiting loop")
                return
            
            if not self._start_ffmpeg():
                self.logger.log("Failed to start FFmpeg stream - exiting loop")
                return
            
            # Create playback device
            self.logger.log("DEBUG: Creating PlaybackDevice")
            self.logger.log(f"DEBUG: Using ALSA device: {self._alsa_device}")
            self.device = miniaudio.PlaybackDevice(
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=self.audio_channels,
                sample_rate=self.audio_sample_rate
            )
            
            self.logger.log(f"Audio playback started: {self.audio_sample_rate}Hz, {self.audio_channels} channels")
            
            # Generator for streaming
            def audio_stream():
                self.logger.log("DEBUG: Generator created and primed")
                channels = self.audio_channels
                sample_width = 2  # 16-bit
                required_frames = yield b""
                
                loop_count = 0
                while not self.stop_event.is_set():
                    loop_count += 1
                    required_bytes = required_frames * channels * sample_width
                    chunk = self.proc.stdout.read(required_bytes)
                    actual_len = len(chunk)
                    self.logger.log(f"DEBUG: Generator loop #{loop_count}: requested {required_frames} frames ({required_bytes} bytes), read {actual_len}")
                    if actual_len < required_bytes:
                        padding = b'\x00' * (required_bytes - actual_len)
                        chunk += padding
                        self.logger.log(f"DEBUG: Padded {len(padding)} bytes of silence")
                    
                    # Quick sample check every 10 loops
                    if loop_count % 10 == 0:
                        try:
                            import struct
                            samples = struct.unpack(f'<{len(chunk)//2}h', chunk)
                            min_val, max_val = min(samples), max(samples)
                            self.logger.log(f"DEBUG: Sample min/max: {min_val}/{max_val}")
                        except:
                            pass
                    
                    required_frames = yield chunk

            # Prime and start
            stream = audio_stream()
            next(stream)
            self.logger.log("DEBUG: Starting device with stream")
            self.device.start(stream)
            self.logger.log("DEBUG: device.start() succeeded")
            
            # Keep thread alive while playing
            while not self.stop_event.is_set() and self.device:
                self.stop_event.wait(0.1)
            
        except Exception as e:
            self.logger.log(f"ERROR in _playback_loop: {e}")
            import traceback
            self.logger.log(f"Traceback: {traceback.format_exc()}")
        finally:
            self.logger.log("DEBUG: _playback_loop finally block")
            self._cleanup()
    
    def start(self) -> bool:
        """
        Start audio playback in a separate thread.
        
        Returns:
            bool: True if audio playback started successfully, False otherwise.
        """
        self.logger.log("DEBUG: Entering start()")
        if not self.audio_available:
            self.logger.log("DEBUG: Audio not available - start() returning False")
            return False
        
        # Start playback thread
        self.logger.log("DEBUG: Launching playback thread")
        self.thread = Thread(target=self._playback_loop, daemon=True)
        self.thread.start()
        self.logger.log("DEBUG: Thread started - returning True")
        return True
    
    def stop(self):
        """
        Stop audio playback and cleanup resources.
        """
        self.logger.log("DEBUG: Entering stop()")
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.logger.log("DEBUG: Joining thread")
            self.thread.join(timeout=1.0)
        
        self._cleanup()
    
    def _cleanup(self):
        """
        Cleanup audio resources and temporary files.
        """
        self.logger.log("DEBUG: Entering _cleanup")
        try:
            if self.device:
                self.logger.log("DEBUG: Stopping and closing device")
                self.device.stop()
                self.device.close()
                self.device = None
            
            if self.proc:
                self.logger.log("DEBUG: Terminating FFmpeg")
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)
                    self.logger.log("DEBUG: FFmpeg terminated gracefully")
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.logger.log("DEBUG: FFmpeg force-killed")
                self.proc = None
            
        except Exception as e:
            self.logger.log(f"Error during cleanup: {e}")
            import traceback
            self.logger.log(f"Traceback in cleanup: {traceback.format_exc()}")
        self.logger.log("DEBUG: Cleanup complete")