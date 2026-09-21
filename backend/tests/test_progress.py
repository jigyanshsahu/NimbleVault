"""
Unit tests for TransferProgressBar and progress formatting utilities.
"""

from __future__ import annotations

import io
import sys
import unittest
from unittest.mock import patch

from app.core import progress
from app.core.progress import TransferProgressBar, format_display_name


class TestTransferProgressBar(unittest.TestCase):
    def test_format_display_name_short(self):
        """Short names under max length should not be truncated."""
        name = "short_video.mp4"
        self.assertEqual(format_display_name(name, 32), name)

    def test_format_display_name_long(self):
        """Long filenames should be middle-truncated with ellipsis."""
        long_name = (
            "35b2420b-a8a3-4ca7-b4fa-62e60dbc9591_30 Most Asked Python "
            "Interview Questions 2025  Python Interview Questions And Answers  Intellipaat_720p.mp4"
        )
        formatted = format_display_name(long_name, 32)
        self.assertLessEqual(len(formatted), 32)
        self.assertIn("...", formatted)
        self.assertTrue(formatted.startswith("35b2420b-a8a3-"))
        self.assertTrue(formatted.endswith(".mp4"))

    def test_tqdm_progress_updates(self):
        """Simulate chunk updates with tqdm enabled."""
        pbar = TransferProgressBar(action="Downloading", name="sample.mp4", total_bytes=1000)
        pbar.update(250)
        pbar.update(500)
        pbar.update(1000)
        pbar.close()
        self.assertEqual(pbar.last_bytes, 1000)
        self.assertTrue(pbar._closed)

    def test_fallback_progress_updates(self):
        """Simulate in-place carriage-return fallback when tqdm is not available."""
        with patch.object(progress, "tqdm", None):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                pbar = TransferProgressBar(action="Uploading", name="sample.mp4", total_bytes=1000)
                pbar.update(500)
                pbar.update(1000)
                pbar.close()
            output = buf.getvalue()
            self.assertIn("Uploading sample.mp4", output)
            self.assertIn("100%", output)
            self.assertTrue(pbar._closed)

    def test_context_manager_lifecycle(self):
        """Ensure context manager properly enters, updates, and closes."""
        with TransferProgressBar(action="Downloading", name="clip.mp4", total_bytes=500) as pbar:
            pbar.update(250)
            pbar.update(500)
            self.assertFalse(pbar._closed)
        self.assertTrue(pbar._closed)


if __name__ == "__main__":
    unittest.main()
