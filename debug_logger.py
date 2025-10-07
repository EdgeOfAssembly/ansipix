"""
debug_logger.py - Flexible Debug Logging Module

This module provides a `DebugLogger` class for easy and conditional debug output.
It supports logging to stderr or a file, can redirect the global `sys.stderr`
stream, and is designed for easy integration with argparse. The class is fully
type-hinted and documented for clarity and maintainability.
"""
import sys
from typing import Union, TextIO, Optional, Any

class DebugLogger:
    """
    A flexible logger for handling debug output.

    Manages the setup and teardown of a debugging stream based on command-line
    arguments. It is best used as a context manager for automatic resource handling.

    Usage:
    ```python
    with DebugLogger(args.debug) as logger:
        if logger.is_active:
            logger.log("This is a debug message.")
    ```
    """
    def __init__(self, debug_arg: Union[bool, str, None], redirect_stderr: bool = False):
        """
        Initializes the DebugLogger.

        Args:
            debug_arg: The debug flag or file path. If True, logs to stderr.
                       If a string, logs to that file path.
            redirect_stderr: If True, redirects the global `sys.stderr` to the
                             debug log stream.
        """
        self.is_active: bool = bool(debug_arg)
        self.redirect_stderr: bool = redirect_stderr
        self._log_stream: Optional[TextIO] = None
        self._original_stderr: TextIO = sys.stderr
        self._should_close_stream: bool = False

        if not self.is_active:
            return

        if isinstance(debug_arg, str):
            try:
                self._log_stream = open(debug_arg, 'w', encoding='utf-8')
                self._should_close_stream = True
            except IOError as e:
                print(f"Error opening debug file '{debug_arg}': {e}", file=sys.stderr)
                self.is_active = False
        else: # If debug_arg is True
            self._log_stream = sys.stderr

        if self.is_active and self.redirect_stderr:
            sys.stderr = self.get_stream()

    def log(self, message: str) -> None:
        """
        Writes a message to the debug stream if logging is active.

        A newline is automatically appended, and the stream is flushed.

        Args:
            message: The debug message to write.
        """
        if self.is_active and self._log_stream:
            print(message, file=self._log_stream)
            self._log_stream.flush()

    def get_stream(self) -> TextIO:
        """
        Returns the active log stream or a dummy stream if inactive.

        Returns:
            The configured log stream or a null stream that discards output.
        """
        if self.is_active and self._log_stream:
            return self._log_stream
        
        class _NullStream:
            def write(self, *args: Any, **kwargs: Any) -> None: pass
            def flush(self, *args: Any, **kwargs: Any) -> None: pass

        return _NullStream() # type: ignore

    def close(self) -> None:
        """
        Closes the log stream and restores sys.stderr if it was redirected.
        Called automatically when used as a context manager.
        """
        if self.redirect_stderr:
            sys.stderr = self._original_stderr

        if self._log_stream and self._should_close_stream:
            self._log_stream.close()
        
        self._log_stream = None
        self.is_active = False

    def __enter__(self) -> 'DebugLogger':
        """Enters the runtime context."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exits the runtime context, ensuring `close()` is called."""
        self.close()