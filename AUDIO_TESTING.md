# Audio Support Testing Guide

This document provides guidance for testing the audio playback functionality in ansipix.

## Prerequisites

1. **ffmpeg** must be installed:
   - Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

2. **Audio device** must be available (speakers or headphones)

## Testing Audio Playback

### 1. Basic Video Playback with Audio (Default)

```bash
ansipix path/to/video.mp4
```

This will play the video with audio by default (if the video has an audio track).

### 2. Disable Audio

```bash
ansipix path/to/video.mp4 --no-audio
```

This disables audio playback.

### 3. With Debug Logging

```bash
ansipix path/to/video.mp4 --debug audio_debug.log
```

Check the debug log to see:
- Whether audio was successfully extracted
- Audio properties (sample rate, channels)
- Any errors during playback

## Expected Behavior

- **Video with audio**: Audio should play in sync with the video frames
- **Video without audio**: Should play normally without errors
- **Missing ffmpeg**: Audio will be disabled with a warning in debug log
- **No audio device**: Audio extraction succeeds but playback may fail (gracefully handled)

## Troubleshooting

### Audio not playing

1. Check if ffmpeg is installed: `ffmpeg -version`
2. Check if video has audio: `ffmpeg -i video.mp4` (look for "Audio:" in output)
3. Check debug log for errors: `ansipix video.mp4 --debug debug.log`

### Audio/Video out of sync

This can happen if:
- Video rendering is slower than real-time (terminal can't keep up)
- System is under heavy load

Try:
- Using a GPU-accelerated terminal (Alacritty recommended)
- Reducing video resolution
- Using a smaller font size

## Implementation Details

The audio subsystem:

1. **Audio Extraction**: Uses ffmpeg to extract audio from video to a temporary WAV file
2. **Low-Latency Playback**: Uses miniaudio library for minimal latency
3. **Thread-Safe**: Audio plays in a separate thread to avoid blocking video rendering
4. **Automatic Cleanup**: Temporary audio files are automatically removed on exit

## Known Limitations

- Audio is only supported for live video playback (not yet for .ansipix files)
- Audio extraction requires ffmpeg to be installed
- First-time extraction may add a small delay before playback starts
- Looping videos will restart audio from the beginning each loop
