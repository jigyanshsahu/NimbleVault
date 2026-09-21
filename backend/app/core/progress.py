"""
NimbleVault – Transfer Progress Bar Utility.
Provides a unified, responsive single-line progress bar for file downloads and uploads.
Supports tqdm when available, with a graceful zero-dependency fallback.
"""

from __future__ import annotations

import shutil
import sys
from typing import Optional

try:
    from tqdm import tqdm
    from tqdm.contrib.logging import logging_redirect_tqdm
except ImportError:
    tqdm = None
    logging_redirect_tqdm = None


def format_display_name(name: str, max_length: int = 32) -> str:
    """
    Truncates overly long filenames cleanly in the middle so terminal lines do not wrap.
    e.g. '35b2420b-a8a3-4ca7-b4fa-62e60dbc9591_30 Most Asked Python.mp4'
         -> '35b2420b-a8a3-...d Python.mp4'
    """
    if len(name) <= max_length:
        return name
    head = (max_length - 3) // 2
    tail = max_length - 3 - head
    return f"{name[:head]}...{name[-tail:]}"


def get_safe_ncols(max_width: int = 95, margin: int = 4) -> int:
    """
    Compute a safe terminal column width for progress bars.

    Why this is needed:
    On Windows consoles (PowerShell / Command Prompt / Terminal), writing to or past
    the very last column of the console buffer automatically wraps the cursor to the
    next line. When a line wraps, carriage return (\\r) only returns the cursor to the
    beginning of the current (wrapped) line instead of moving up to the original row.
    This causes every subsequent chunk update to print on a brand-new line.

    By capping the width and reserving a safety margin of at least 4 characters,
    the progress bar never reaches the terminal boundary and stays strictly on a single line.
    """
    try:
        cols = shutil.get_terminal_size((80, 20)).columns
        return max(40, min(cols - margin, max_width))
    except Exception:
        return 80


class TransferProgressBar:
    """
    Dynamic progress tracker for chunked streaming downloads & uploads.
    Guarantees a clean single-line display across all terminals and prevents
    interleaved log messages or terminal auto-wraps from duplicating lines.
    """

    def __init__(
        self,
        action: str,
        name: str,
        total_bytes: Optional[int] = None,
        file: Optional[object] = None,
    ) -> None:
        self.action = action
        self.display_name = format_display_name(name)
        self.total_bytes = total_bytes
        self.last_bytes = 0
        self._desc = f"{self.action} {self.display_name}"
        self._closed = False
        self._target_file = file or sys.stdout
        self._log_redirect = None

        if tqdm is not None:
            # Safely capture any logger messages during transfer so they don't break \r
            if logging_redirect_tqdm is not None:
                try:
                    self._log_redirect = logging_redirect_tqdm()
                    self._log_redirect.__enter__()
                except Exception:
                    self._log_redirect = None

            safe_ncols = get_safe_ncols()
            self._pbar = tqdm(
                total=self.total_bytes,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=self._desc,
                leave=True,
                file=self._target_file,
                ncols=safe_ncols,
            )
        else:
            self._pbar = None

    def write(self, s: str) -> None:
        """Write a message without breaking the in-place progress bar."""
        if self._pbar is not None:
            self._pbar.write(s, file=self._target_file)
        else:
            self._target_file.write(f"\r\033[K{s}\n")
            self._target_file.flush()

    def update(self, current_bytes: int, total_bytes: Optional[int] = None) -> None:
        """Update progress with current bytes transferred and optional total bytes."""
        if self._closed:
            return

        if total_bytes and not self.total_bytes:
            self.total_bytes = total_bytes
            if self._pbar is not None and self._pbar.total is None:
                self._pbar.total = total_bytes
                self._pbar.refresh()

        delta = current_bytes - self.last_bytes
        self.last_bytes = current_bytes

        if self._pbar is not None:
            if delta > 0:
                self._pbar.update(delta)
        else:
            self._render_fallback(current_bytes)

    def _render_fallback(self, current_bytes: int) -> None:
        """Render a clean in-place carriage-return bar when tqdm is unavailable."""
        if self.total_bytes and self.total_bytes > 0:
            pct = int((current_bytes / self.total_bytes) * 100)
            bar_len = 20
            filled = int(bar_len * current_bytes // self.total_bytes)
            bar = "=" * filled + (">" if filled < bar_len else "") + " " * (bar_len - filled - (1 if filled < bar_len else 0))
            cur_mb = current_bytes / (1024 * 1024)
            tot_mb = self.total_bytes / (1024 * 1024)
            msg = f"\r{self._desc}: [{bar}] {pct:3d}% ({cur_mb:.1f}/{tot_mb:.1f} MB)"
        else:
            cur_mb = current_bytes / (1024 * 1024)
            msg = f"\r{self._desc}: {cur_mb:.1f} MB transferred"

        self._target_file.write(msg)
        self._target_file.flush()

    def close(self) -> None:
        """Finalize the progress display."""
        if self._closed:
            return
        self._closed = True

        if self._pbar is not None:
            if self.total_bytes and self.last_bytes < self.total_bytes:
                self._pbar.update(self.total_bytes - self.last_bytes)
            self._pbar.close()
        else:
            self._target_file.write("\n")
            self._target_file.flush()

        if self._log_redirect is not None:
            try:
                self._log_redirect.__exit__(None, None, None)
            except Exception:
                pass
            self._log_redirect = None

    def __enter__(self) -> TransferProgressBar:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
