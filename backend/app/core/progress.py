"""
NimbleVault – Transfer Progress Bar Utility.
Provides a unified, responsive single-line progress bar for file downloads and uploads.
Supports tqdm when available, with a graceful zero-dependency fallback.
"""

from __future__ import annotations

import sys
from typing import Optional

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


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


class TransferProgressBar:
    """
    Dynamic progress tracker for chunked streaming downloads & uploads.
    """

    def __init__(
        self,
        action: str,
        name: str,
        total_bytes: Optional[int] = None,
    ) -> None:
        self.action = action
        self.display_name = format_display_name(name)
        self.total_bytes = total_bytes
        self.last_bytes = 0
        self._desc = f"{self.action} {self.display_name}"
        self._closed = False

        if tqdm is not None:
            self._pbar = tqdm(
                total=self.total_bytes,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=self._desc,
                leave=True,
                file=sys.stdout,
                dynamic_ncols=True,
            )
        else:
            self._pbar = None

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
            sys.stdout.write(f"\r{self._desc}: [{bar}] {pct:3d}% ({cur_mb:.1f}/{tot_mb:.1f} MB)")
        else:
            cur_mb = current_bytes / (1024 * 1024)
            sys.stdout.write(f"\r{self._desc}: {cur_mb:.1f} MB transferred")
        sys.stdout.flush()

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
            sys.stdout.write("\n")
            sys.stdout.flush()

    def __enter__(self) -> TransferProgressBar:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
