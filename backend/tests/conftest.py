"""Pytest configuration."""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only-32chars")
os.environ.setdefault("MARKET_DATA_MOCK_ENABLED", "false")
os.environ.setdefault("NEWS_MOCK_ENABLED", "false")
