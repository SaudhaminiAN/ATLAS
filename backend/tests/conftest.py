"""Pytest configuration."""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only-32chars")
