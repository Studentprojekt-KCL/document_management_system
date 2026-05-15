"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for GitHub connector helpers (including internal methods).
"""

# Tests intentionally call private helpers on GitHub for focused checks.
# pylint: disable=protected-access

import asyncio
import base64
import io
import json
import unittest
import zipfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from interfacer_github import GitHub


def _make_zip(files: dict[str, str]) -> bytes:
    """Build an in-memory zip with the given path->content mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    return buf.getvalue()


def _fake_stream_client(zip_bytes: bytes, status_code: int = 200) -> MagicMock:
    """Return a mock httpx.AsyncClient whose stream() yields the given zip bytes."""
    response = MagicMock()
    response.status_code = status_code
    response.aread = AsyncMock(return_value=zip_bytes)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)

    client = MagicMock()
    client.stream.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestGitHubHelpers(unittest.TestCase):
    """Tests for GitHub connector URL and auth helpers."""

    def setUp(self) -> None:
        self.github = GitHub()

    def test_defined_fields_matches_gitlab_contract_shape(self) -> None:
        """Schema keys overlap GitLab connector (base fields + extensions from file_types)."""
        keys = list(self.github.defined_fields.keys())
        self.assertIn("content", keys)
        self.assertIn("unique_pointer", keys)
        self.assertIn("source_system", keys)

    def test_make_and_parse_pointer_roundtrip(self) -> None:
        """File pointer URL encodes and decodes to the same components."""
        pointer = self.github._make_file_pointer("owner/repo", "src/file.py", "main")
        parsed = self.github._parse_file_pointer(pointer)
        self.assertEqual(parsed, ("owner/repo", "src/file.py", "main"))

    def test_decode_invalid_base64_maps_to_legacy_floor(self) -> None:
        """Invalid subdata base64 is treated like a legacy watermark at UTC minimum (re-index all)."""
        repo_map, legacy_floor = GitHub._decode_subdata("this-is-not-base64")
        self.assertEqual(repo_map, {})
        self.assertEqual(legacy_floor, datetime.min.replace(tzinfo=timezone.utc))

    def test_decode_json_repo_map_preserves_legacy_absent(self) -> None:
        """JSON object subdata behaves like GitLab — per-repo last ``pushed_at`` snapshot."""
        payload = {"org/a": "2024-06-01T12:00:00Z", "org/b": "2025-01-02T09:00:00+00:00"}
        encoded = GitHub._generate_subdata(payload)
        repo_map, legacy = GitHub._decode_subdata(encoded)
        self.assertIsNone(legacy)
        self.assertEqual(repo_map, payload)

    def test_decode_legacy_single_iso_timestamp(self) -> None:
        """Older deployments encoded a single global ISO watermark only."""
        token = base64.urlsafe_b64encode(b"2026-04-01T00:00:00+00:00").decode()
        repo_map, legacy = GitHub._decode_subdata(token)
        self.assertEqual(repo_map, {})
        assert legacy is not None
        self.assertEqual(
            legacy,
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )


class TestGitHubStreaming(unittest.TestCase):
    """Tests for the async streaming path."""

    _REPO = {
        "full_name": "owner/repo",
        "pushed_at": "2026-03-01T00:00:00Z",
        "default_branch": "main",
    }
    _STALE_WATERMARK_SUBDATA = GitHub._generate_subdata({"owner/repo": "2026-04-01T00:00:00+00:00"})

    def setUp(self) -> None:
        self.github = GitHub()

    def _collect(self, gen) -> list[dict]:
        async def run():
            return [json.loads(chunk) async for chunk in gen]

        return asyncio.run(run())

    def test_stream_yields_subdata_first_then_files(self) -> None:
        """First yielded chunk is the subdata header; subsequent chunks are file objects."""
        zip_bytes = _make_zip({"repo-main/src/file.py": "print('hello')"})
        self.github._get_repos = lambda _=None: [self._REPO]

        with patch("interfacer_github.httpx.AsyncClient", return_value=_fake_stream_client(zip_bytes)):
            chunks = self._collect(self.github.stream_files_to_index())

        self.assertIn("subdata", chunks[0])
        first_map = json.loads(base64.urlsafe_b64decode(chunks[0]["subdata"]))
        self.assertEqual(first_map["owner/repo"], "2026-03-01T00:00:00Z")
        self.assertGreater(len(chunks), 1)
        self.assertIn("content", chunks[1])
        self.assertIn("metadata", chunks[1])

    def test_stream_filters_repos_older_than_subdata(self) -> None:
        """Repos with pushed_at older than recorded subdata watermark produce no file chunks."""
        old_repo = {**self._REPO, "pushed_at": "2026-01-01T00:00:00Z"}
        self.github._get_repos = lambda _=None: [old_repo]

        chunks = self._collect(self.github.stream_files_to_index(subdata=self._STALE_WATERMARK_SUBDATA))

        self.assertEqual(len(chunks), 1)
        self.assertIn("subdata", chunks[0])

    def test_stream_non_200_does_not_break_other_repos(self) -> None:
        """A failed download for one repo does not prevent other repos from being processed."""
        zip_bytes = _make_zip({"repo-main/file.txt": "data"})
        repos = [
            {**self._REPO, "full_name": "owner/bad", "pushed_at": "2026-03-01T00:00:00Z"},
            {**self._REPO, "full_name": "owner/good", "pushed_at": "2026-03-02T00:00:00Z"},
        ]
        self.github._get_repos = lambda _=None: repos

        bad_response = MagicMock()
        bad_response.status_code = 404
        bad_response.__aenter__ = AsyncMock(return_value=bad_response)
        bad_response.__aexit__ = AsyncMock(return_value=False)

        good_response = MagicMock()
        good_response.status_code = 200
        good_response.aread = AsyncMock(return_value=zip_bytes)
        good_response.__aenter__ = AsyncMock(return_value=good_response)
        good_response.__aexit__ = AsyncMock(return_value=False)

        client = MagicMock()
        client.stream.side_effect = [bad_response, good_response]
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("interfacer_github.httpx.AsyncClient", return_value=client):
            chunks = self._collect(self.github.stream_files_to_index())

        file_chunks = [c for c in chunks if "content" in c]
        self.assertEqual(len(file_chunks), 1)

    def test_unzip_worker_delegates_to_thread(self) -> None:
        """_unzip_files runs _unpack_zip via asyncio.to_thread to avoid blocking the event loop."""
        zip_queue: asyncio.Queue = asyncio.Queue()
        output_queue: asyncio.Queue = asyncio.Queue()
        fake_files = [{"content": "abc", "metadata": {"name": "file.py"}}]

        asyncio.run(zip_queue.put({"data": b"zip", "full_name": "owner/repo", "branch": "main"}))
        asyncio.run(zip_queue.put(None))

        async def run():
            with patch("interfacer_github.asyncio.to_thread", new=AsyncMock(return_value=fake_files)):
                await self.github._unzip_files(zip_queue, output_queue)

        asyncio.run(run())
        result = asyncio.run(output_queue.get())
        self.assertEqual(result, fake_files)

    def test_get_repos_called_via_to_thread(self) -> None:
        """stream_files_to_index delegates _get_repos to asyncio.to_thread."""

        async def passthrough(fn, *args):
            return fn(*args)

        async def run():
            self.github._get_repos = lambda _=None: []
            with patch("interfacer_github.asyncio.to_thread", side_effect=passthrough) as mock_thread:
                async for _ in self.github.stream_files_to_index():
                    pass
                return mock_thread.call_args_list

        calls = asyncio.run(run())
        self.assertTrue(len(calls) >= 1)
        first_fn = calls[0][0][0]
        self.assertIs(first_fn, self.github._get_repos)
