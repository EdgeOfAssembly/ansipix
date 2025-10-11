# ansipix - High-Performance Terminal Media Viewer

![ansipix demo](https://user-images.githubusercontent.com/12345/67890.gif) <!-- Placeholder for a cool demo GIF -->

**Authored by:** EdgeOfAssembly  
**Contact:** [haxbox2000@gmail.com](mailto:haxbox2000@gmail.com)  
**Date:** 2025-10-07

`ansipix` is a powerful, command-line utility for rendering images, animated GIFs, and videos directly in your terminal using 24-bit "truecolor" ANSI art. It is designed for high performance, with a special focus on smooth video playback and an efficient custom file format for pre-rendered animations.

## 🎬 Sample Videos Converted to Terminal ANSI Art

Get a taste of what your videos will look like when converted to vivid ANSI art for the terminal! Check out these samples:

- [Sample 1](https://drive.google.com/file/d/1fPeoOwCXe52MvtfyQxmDcpeyxlsQeFLI/view)
- [Sample 2](https://drive.google.com/file/d/1ISAlvCLuHWLahWl8lZuQjXXIv_JKhw6u/view)
- [Sample 3](https://drive.google.com/file/d/1LANmGEg8V0yWHEkaQBGj9rpDI-rU8HpJ/view)

There is also a ready pre-rendered `.ansipix` file that you can download from here:
- [cyber_JetBrains_Mono_Regular_8pt.ansipix.zst](https://drive.google.com/file/d/1vEiPl1gPYAtEwtqslHGmkkl9OycPXBzn/view)

Settings used to create that `.ansipix` file:
```
Font:           JetBrains Mono Regular (recommended but of course you can use any font)
Size:           8pt
Terminal:       LXTerminal (Alacritty recommended)
```

After downloading, unzip it like this:
```bash
zstd -d cyber_JetBrains_Mono_Regular_8pt.ansipix.zst
```
And then if you installed `ansipix` with pip, just run:
```bash
ansipix cyber_JetBrains_Mono_Regular_8pt.ansipix
```

*Later I will update the `ansipix` file specification to have meta-data for the used font, font-size, and maybe a compression scheme.*

---

### Installation

The recommended way to install `ansipix` is using `pip`:

```bash
pip install ansipix
```

This will automatically install the package and all its dependencies, making the `ansipix` command available in your terminal.

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

## 🚀 Performance & Configuration Recommendations

`ansipix` is highly optimized and can generate ANSI data faster than many terminals can draw it. The playback speed is therefore **bound by the performance of your terminal emulator**. For the best experience, especially with high-resolution or high-FPS videos, a GPU-accelerated terminal is **highly recommended**.

### Recommended Terminal Configurations

-   **Alacritty (High-Speed Performance):** For blazing fast rendering, [Alacritty](https://alacritty.org/) is the top choice. Use this optimal configuration for the best results:
    -   [alacritty.toml (Google Drive)](https://drive.google.com/file/d/1TNYd7llQqP-FVV-3z0JL-QgEu6NG5bro/view)

-   **KMSCON (For Pure Virtual Console):** If you prefer running `ansipix` without Xorg, use [kmscon](https://github.com/Aetf/kmscon) with this tuned configuration:
    -   [kmscon.conf (Google Drive)](https://drive.google.com/file/d/16JNnaaoCMCQzo3t8yLcDo8X00DoAtmX2/view)

### Recommended Monospace Fonts for Terminal ANSI Art

For the best possible quality and experience, use one of these top-rated fonts optimized for ANSI art:

1.  **JetBrains Mono**
    -   *Superb clarity and perfect box-drawing support*
2.  **Fira Mono**
    -   *Crisp, consistent, and excellent for ANSI graphics*
3.  **Fira Code**
    -   *Outstanding rendering (disable ligatures for pure ANSI art)*
4.  **Hack**
    -   *Reliable and clear, designed for coding and terminal use*

---

## Resource Usage Warning

**Important:** The offline rendering process (`--output file.ansipix`) can consume a very large amount of RAM and disk space.

The `.ansipix` format stores uncompressed ANSI text data for every single frame. Using a smaller font size dramatically increases the character count, leading to exponentially larger files.

**Real-World Example:** A **22 MB** WebM video (922 frames) rendered with a **4pt** font resulted in a **2.1 GB** `.ansipix` file.

Please follow these recommendations when creating `.ansipix` files:
-   **Start with short video clips** (e.g., under 10 seconds).
-   **Use a reasonable font size (8pt or larger)**.
-   A GPU-accelerated terminal like **[Alacritty](https://alacritty.org/)** is strongly recommended for playback of high-density files.

---

## Usage Examples

### 1. Live Playback
Play any supported image, GIF, or video directly. Press `Ctrl+C` at any time to exit.

```bash
# Play a static image
ansipix path/to/my_image.png

# Play an animated GIF (loops infinitely by default)
ansipix path/to/animation.gif

# Play a video with audio (requires ffmpeg)
ansipix path/to/my_video.mp4

# Play a video without audio
ansipix path/to/my_video.mp4 --no-audio

# Play a video and loop it 3 times
ansipix path/to/my_video.mp4 --loop 3
```

### 2. Creating an `.ansipix` File
Render a video into the custom file format. This will use all your CPU cores for the fastest possible processing.

```bash
# Convert a video to an .ansipix file
ansipix my_video.webm --output my_video.ansipix
```

### 3. Playing an `.ansipix` File
Play a pre-rendered file. This is the most efficient way to watch, using very little CPU.

```bash
# Play the file you just created
ansipix my_video.ansipix

# Play the file and override the saved loop setting to loop infinitely
ansipix my_video.ansipix --loop 0
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
                        Downsampling method for OpenCV resizing (default: area).
  --profile PROFILE     Profile the execution and save to specified file.
```

---

## Current Limitations & Future Work

-   **Unimplemented Arguments:** `--width`, `--height`, and `--full-width` are placeholders and do not affect output size.
-   **Limited Audio Support:** Audio is now supported for live video playback only (not yet for `.ansipix` files). Requires `ffmpeg` to be installed for audio extraction.
-   **No Playback Controls:** Pausing, seeking, or adjusting speed is not yet implemented.
-   **Image/GIF Offline Rendering:** The `--output` flag is not yet complete for static images or GIFs.
-   **Code Refactoring:** Future work includes unifying rendering pipelines to reduce code duplication.

---

## Dependencies

To run `ansipix`, you need Python 3 and the following packages:

```bash
pip install opencv-python numpy Pillow miniaudio
```

**Optional but Recommended:**
- `ffmpeg` - Required for audio playback in videos. Install via your package manager:
  - **Ubuntu/Debian:** `sudo apt-get install ffmpeg`
  - **macOS:** `brew install ffmpeg`
  - **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html)

---

## License

`ansipix` is released under a dual-license model.

### For Open-Source Projects
For use in open-source projects, `ansipix` is licensed under the **GNU General Public License v3.0**.

### For Commercial and Closed-Source Use
For use in any commercial and/or closed-source application, a separate commercial license is required. Please contact me to arrange a license.

**Author:** EdgeOfAssembly  
**Contact:** [haxbox2000@gmail.com](mailto:haxbox2000@gmail.com)