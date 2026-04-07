"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for GitHub connector helpers (including internal methods).
"""

# Tests intentionally call private helpers on GitHub for focused checks.
# pylint: disable=protected-access

import base64
import os
import unittest
from unittest.mock import patch

from interfacer_github import GitHub
from unpacker import unpack_values


class TestUnpacker(unittest.TestCase):
    """Tests for unpack_values helper."""

    def test_unpack_values_returns_nested_value(self) -> None:
        """Nested dict path returns the leaf value."""
        data = {"a": {"b": {"c": 123}}}
        self.assertEqual(unpack_values(data, ("a", "b", "c")), 123)

    def test_unpack_values_returns_none_for_missing_path(self) -> None:
        """Missing key in path yields None."""
        data = {"a": {"b": 1}}
        self.assertIsNone(unpack_values(data, ("a", "x")))


class TestGitHubHelpers(unittest.TestCase):
    """Tests for GitHub connector URL and auth helpers."""

    def setUp(self) -> None:
        self.github = GitHub()

    def test_make_and_parse_pointer_roundtrip(self) -> None:
        """File pointer URL encodes and decodes to the same components."""
        pointer = self.github._make_file_pointer("owner/repo", "src/file.py", "main")
        parsed = self.github._parse_file_pointer(pointer)
        self.assertEqual(parsed, ("owner/repo", "src/file.py", "main"))

    def test_provided_date_invalid_base64_returns_min_datetime(self) -> None:
        """Invalid subdata base64 falls back to minimum UTC datetime."""
        dt = GitHub._provided_date("this-is-not-base64")
        encoded = base64.b64encode(dt.isoformat().encode("utf-8")).decode("utf-8")
        self.assertTrue(isinstance(encoded, str))

    def test_auth_mode_legacy_uses_github_token(self) -> None:
        """Legacy mode sets Authorization from GITHUB_TOKEN."""
        with patch.dict(
            os.environ,
            {"GITHUB_AUTH_MODE": "legacy", "GITHUB_TOKEN": "legacy-token"},
            clear=False,
        ):
            github = GitHub()
        self.assertEqual(github.session.headers.get("Authorization"), "Bearer legacy-token")

    def test_auth_mode_app_uses_app_installation_token(self) -> None:
        """App mode sets Authorization from installation token env."""
        with patch.dict(
            os.environ,
            {"GITHUB_AUTH_MODE": "app", "GITHUB_APP_INSTALLATION_TOKEN": "app-token"},
            clear=False,
        ):
            github = GitHub()
        self.assertEqual(github.session.headers.get("Authorization"), "Bearer app-token")

    def test_auth_mode_auto_prefers_app_token(self) -> None:
        """Auto mode prefers app installation token over legacy token."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_AUTH_MODE": "auto",
                "GITHUB_TOKEN": "legacy-token",
                "GITHUB_APP_INSTALLATION_TOKEN": "app-token",
            },
            clear=False,
        ):
            github = GitHub()
        self.assertEqual(github.session.headers.get("Authorization"), "Bearer app-token")
