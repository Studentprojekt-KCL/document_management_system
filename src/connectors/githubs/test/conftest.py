"""Pytest configuration for GitHub connector tests."""

import pytest


@pytest.fixture(autouse=True)
def github_env(monkeypatch):
    """Provide required env vars so GitHub() can be instantiated in tests."""
    monkeypatch.setenv("GITHUB_API_URL", "https://api.github.test/")
    monkeypatch.setenv("GITHUB_SYSTEM_NAME", "test")
    monkeypatch.setenv("GITHUB_API_VERSION", "2022-11-28")
    monkeypatch.setenv("GITHUB_AUTH_MODE", "auto")
