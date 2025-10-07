# ansipix - High-Performance Terminal Media Viewer

![ansipix demo](https://user-images.githubusercontent.com/12345/67890.gif) <!-- Placeholder for a cool demo GIF -->

**Authored by:** EdgeOfAssembly  
**Contact:** [haxbox2000@gmail.com](mailto:haxbox2000@gmail.com)  
**Date:** 2025-10-07

`ansipix` is a powerful, command-line utility for rendering images, animated GIFs, and videos directly in your terminal using 24-bit "truecolor" ANSI art. It is designed for high performance, with a special focus on smooth video playback and an efficient custom file format for pre-rendered animations.

---

## Features

-   **Versatile Media Support:** Plays static images (PNG, JPG), animated GIFs, and major video formats (MP4, WebM, MKV).
-   **Truecolor Rendering:** Utilizes 24-bit color ANSI escape codes to produce rich, accurate colors in compatible terminals.
-   **High-Performance Live Rendering:** Features a highly optimized pipeline for converting media to ANSI art in real-time.
-   **Custom `.ansipix` File Format:**
    -   Save any video or image as a portable, pre-rendered `.ansipix` file.
    -   Includes all metadata (dimensions, frame timings, loop count) for perfect, repeatable playback.
    -   **Extremely fast playback** that uses minimal CPU, as all rendering is done ahead of time.
-   **Parallelized Offline Rendering:** Creates `.ansipix` files at maximum speed by using `multiprocessing` to leverage all available CPU cores.
-   **Graceful Exit:** The program can be safely terminated at any time by pressing `Ctrl+C`, which will restore your terminal to its normal state.
-   **Configurable Playback:**
    -   Animations and videos loop infinitely by default. Use the `--loop` argument to specify a set number of repetitions.
    -   The `area` downsampling method is used by default for a good balance of quality and speed. This can be changed with `--downsample-method` (e.g., `nearest`) for potentially faster rendering at the cost of quality.
-   **Developer Tools:** Includes built-in `--debug` and `--profile` flags for easy troubleshooting and performance analysis.

---

## Performance Recommendations

`ansipix` is highly optimized and can generate ANSI data faster than many terminals can draw it. The playback speed is therefore **bound by the performance of your terminal emulator**.

For the best experience, especially with high-resolution or high-FPS videos, a GPU-accelerated terminal is **highly recommended**.

I personally recommend **[Alacritty](https://alacritty.org/)**, as it is one of the fastest terminals available and provides an exceptionally smooth viewing experience with `ansipix`.

---

## Resource Usage Warning

**Important:** The offline rendering process (`--output file.ansipix`) can consume a very large amount of RAM and disk space.

The `.ansipix` format stores uncompressed ANSI text data for every single frame. The amount of data generated is directly proportional to the number of characters on the screen. Using a smaller font size dramatically increases the character count, leading to exponentially larger files.

**Real-World Example:** During testing, a **22 MB** WebM video (922 frames, 36 seconds) rendered with a **4pt** monospace font resulted in a **2.1 GB** `.ansipix` file and consumed a significant amount of memory during creation.

Please follow these recommendations when creating `.ansipix` files:
-   **Start with short video clips** (e.g., under 10 seconds) to gauge the output size.
-   **Use a reasonable font size (8pt or larger)** for your initial tests. Avoid very small font sizes unless you are prepared for massive file sizes.
-   Playback of these large, high-density `.ansipix` files is also very demanding on the terminal. A GPU-accelerated terminal like **[Alacritty](https://alacritty.org/)** is strongly recommended for a smooth experience.

The author plans to investigate optimizations for the offline rendering process in a future release.

---

## Usage Examples

### 1. Live Playback
Play any supported image, GIF, or video directly. Press `Ctrl+C` at any time to exit.

```bash
# Play a static image
python3 ansipix.py path/to/my_image.png

# Play an animated GIF (loops infinitely by default)
python3 ansipix.py path/to/animation.gif

# Play a video and loop it 3 times
python3 ansipix.py path/to/my_video.mp4 --loop 3
```

### 2. Creating an `.ansipix` File
Render a video into the custom file format. This will use all your CPU cores for the fastest possible processing.

```bash
# Convert a video to an .ansipix file
python3 ansipix.py my_video.webm --output my_video.ansipix
```

### 3. Playing an `.ansipix` File
Play a pre-rendered file. This is the most efficient way to watch, using very little CPU.

```bash
# Play the file you just created (will use the loop setting saved in the file)
python3 ansipix.py my_video.ansipix

# Play the file and override the saved loop setting to loop infinitely
python3 ansipix.py my_video.ansipix --loop 0
```

---

## Command-Line Options

```
usage: ansipix.py [-h] [--width WIDTH] [--height HEIGHT] [-o OUTPUT] [--loop LOOP] [--debug DEBUG] [--background BACKGROUND] [--tile]
                  [--full-width] [--buffer-percent BUFFER_PERCENT] [--downsample-method {nearest,linear,cubic,area,lanczos4}]
                  [--profile PROFILE]
                  image_path

Render an image, animated GIF, or video in the terminal.

positional arguments:
  image_path            Path to the input image, GIF, video, or .ansipix file.

options:
  -h, --help            show this help message and exit
  --width WIDTH         Optional target terminal width in characters (auto-detects otherwise).
  --height HEIGHT       Optional target terminal height in lines (auto-detects otherwise).
  -o OUTPUT, --output OUTPUT
                        Optional output file path. If provided, save the ANSI art to this file instead of printing to console.
  --loop LOOP           Number of times to loop the GIF or video animation (0 for infinite, default: 0).
  --debug DEBUG         Save debug output to the specified file.
  --background BACKGROUND
                        Optional background: solid color (name or hex like ff00ff) or image path.
  --tile                Tile the background image instead of stretching.
  --full-width          Use full terminal width and aspect-based height (may require scrolling if taller than terminal).
  --buffer-percent BUFFER_PERCENT
                        Percentage of free RAM to use for pre-buffering (0-100, default 10).
  --downsample-method {nearest,linear,cubic,area,lanczos4}
                        Downsampling method for OpenCV resizing (default: area). Supported: nearest, linear, cubic, area, lanczos4.
  --profile PROFILE     Profile the execution and save to specified file.
```

---

## Current Limitations & Future Work

This project is fully functional for its core purpose, but there are several areas that are not yet implemented or fully tested.

-   **Unimplemented Arguments:** The `--width`, `--height`, and `--full-width` arguments are currently placeholders and do not affect the output size. The renderer will always auto-fit to the terminal dimensions.
-   **Missing Sound Support:** The player renders video only. Audio from video files is ignored.
-   **Missing Playback Controls:** There are no controls for pausing, seeking, or adjusting speed during playback. This is a planned feature for a future release.
-   **Image/GIF Offline Rendering:** The offline rendering pipeline (`--output file.ansipix`) is fully implemented for videos but is not yet complete for static images or GIFs.
-   **Code Refactoring:** The `image_player.py` module contains a separate, more complex rendering pipeline for handling backgrounds and transparency. In the future, this could be unified with the main `render.py` module to reduce code duplication.

---

## Dependencies

To run `ansipix`, you need Python 3 and the following packages, which can be installed via pip:

```bash
pip install opencv-python numpy Pillow
```

---

## License

`ansipix` is released under a dual-license model.

### For Open-Source Projects
For use in open-source projects, `ansipix` is licensed under the **GNU General Public License v3.0**. You are free to use, modify, and distribute it in your open-source projects, provided you comply with the terms of the GPLv3.

### For Commercial and Closed-Source Use
For use in any commercial and/or closed-source application, a separate commercial license is required. Please contact me to arrange a license that fits your needs.

**Author:** EdgeOfAssembly  
**Contact:** [haxbox2000@gmail.com](mailto:haxbox2000@gmail.com)