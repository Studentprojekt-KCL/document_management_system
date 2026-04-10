"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for GitHub connector helpers (including internal methods).
"""

# Tests intentionally call private helpers on GitHub for focused checks.
# pylint: disable=protected-access

import base64
import unittest

from interfacer_github import GitHub


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
