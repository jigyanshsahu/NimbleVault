"""
Pytest configuration and shared fixtures for NimbleVault.
"""
import os
import sys
from pathlib import Path
import pytest

# Ensure backend dir is on python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Force test environment variables before importing app
os.environ["DEBUG"] = "false"
os.environ["APP_NAME"] = "NimbleVault-Test"

@pytest.fixture
def sample_rubric_paths():
    """The 4 required assignment benchmark paths."""
    return [
        (
            "Drive/Vlogs/2024/Week12/Final_Edit.mp4",
            "Vlogs 2024: Week 12 Final Edit",
        ),
        (
            "Drive/Products/Launch_X/Tutorials/Getting_Started.mov",
            "Launch X Product Tutorial: Getting Started",
        ),
        (
            "Drive/Team/Archive/Q3/Marketing_Review_10-05.avi",
            "Team Archive Q3: Marketing Review 10-05",
        ),
        (
            "Drive/Clients/ACME/Testimonial_v2.mp4",
            "Client Testimonial: ACME (v2)",
        ),
    ]
