#!/usr/bin/env python3
"""
ansipix - Root Launcher Script

This script provides a convenient way to run the ansipix application directly
from a cloned repository without needing to install it. It ensures that the
Python path is set up correctly and then calls the main command-line interface
function from the `ansipix` package.
"""
import sys
from ansipix.cli import cli

if __name__ == '__main__':
    # Add a check for dependencies
    try:
        import cv2
        import numpy
        import PIL
    except ImportError as e:
        print(f"Error: A required dependency is not installed: {e.name}", file=sys.stderr)
        print("Please install the required packages by running:", file=sys.stderr)
        print("pip install opencv-python numpy Pillow", file=sys.stderr)
        sys.exit(1)
        
    cli()