"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the gateway connector service.
"""

# Tests intentionally call private helpers on Connector for focused checks.
# pylint: disable=protected-access

import base64
import unittest
import unittest.mock
from unittest.mock import AsyncMock, MagicMock

import httpx

from gateway.schemas import InputItem
from gateway.services.connector import Connector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connector(url: str = "http://connector", timeout: int = 120) -> Connector:
    """Return a Connector with a mock async HTTP client."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    return Connector(url=url, client=mock_client, timeout=timeout)


def _encode(text: str) -> str:
    """Base64-encode a string as the connector would return it."""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def _mock_response(mock_client: AsyncMock, data: list[dict]) -> None:
    """Configure mock_client.post to return a valid JSON response."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = data
    mock_client.post.return_value = mock_resp


def _mock_error(mock_client: AsyncMock, error: Exception) -> None:
    """Configure mock_client.post to raise an exception."""
    mock_client.post.side_effect = error


GITLAB_POINTER = "https://gitlab.dms-lookup.com/api/v4/projects/7/repository/files/doc.txt"


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConnectorInit(unittest.TestCase):
    """Tests for Connector.__init__."""

    def test_url_is_stored(self) -> None:
        c = _make_connector(url="http://example.com")
        self.assertEqual(c.url, "http://example.com")

    def test_timeout_is_stored(self) -> None:
        c = _make_connector(timeout=60)
        self.assertEqual(c.timeout, 60)

    def test_default_timeout(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        c = Connector(url="http://connector", client=mock_client)
        self.assertEqual(c.timeout, 120)

    def test_client_is_stored(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        c = Connector(url="http://connector", client=mock_client)
        self.assertIs(c.client, mock_client)


# ---------------------------------------------------------------------------
# get_file_contents
# ---------------------------------------------------------------------------


class TestGetFileContents(unittest.IsolatedAsyncioTestCase):
    """Tests for Connector.get_file_contents."""

    async def test_returns_input_items(self) -> None:
        """Returns a list of InputItem on success."""
        c = _make_connector()
        _mock_response(c.client, [{"content": _encode("hello world"), "unique_pointer": GITLAB_POINTER}])
        result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], InputItem)

    async def test_decoded_content_is_correct(self) -> None:
        """Decoded content matches the original text."""
        c = _make_connector()
        _mock_response(c.client, [{"content": _encode("Top secret data."), "unique_pointer": GITLAB_POINTER}])
        result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(result[0].content, "Top secret data.")

    async def test_pointer_stored_in_metadata(self) -> None:
        """unique_pointer from response is stored in item metadata."""
        c = _make_connector()
        _mock_response(c.client, [{"content": _encode("content"), "unique_pointer": GITLAB_POINTER}])
        result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(result[0].metadata.unique_pointer, GITLAB_POINTER)

    async def test_posts_to_correct_url(self) -> None:
        """Posts to <url>/get_files."""
        c = _make_connector(url="http://connector")
        _mock_response(c.client, [{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        await c.get_file_contents([GITLAB_POINTER])
        called_url = c.client.post.call_args[0][0]
        self.assertEqual(called_url, "http://connector/get_files")

    async def test_trailing_slash_in_url_is_stripped(self) -> None:
        """Trailing slash in url is stripped before appending /get_files."""
        c = _make_connector(url="http://connector/")
        _mock_response(c.client, [{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        await c.get_file_contents([GITLAB_POINTER])
        called_url = c.client.post.call_args[0][0]
        self.assertEqual(called_url, "http://connector/get_files")

    async def test_include_content_param_is_true(self) -> None:
        """Request params include include_content=True."""
        c = _make_connector()
        _mock_response(c.client, [{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        await c.get_file_contents([GITLAB_POINTER])
        params = c.client.post.call_args[1]["params"]
        self.assertIn(("include_content", True), params)

    async def test_pointers_sent_in_payload(self) -> None:
        """file_pointers are sent in the JSON body."""
        c = _make_connector()
        _mock_response(c.client, [{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        pointers = [GITLAB_POINTER]
        await c.get_file_contents(pointers)
        payload = c.client.post.call_args[1]["json"]
        self.assertEqual(payload["file_pointers"], pointers)

    async def test_multiple_pointers_return_multiple_items(self) -> None:
        """One InputItem is returned per pointer."""
        c = _make_connector()
        _mock_response(
            c.client,
            [
                {"content": _encode("doc one"), "unique_pointer": "ptr-1"},
                {"content": _encode("doc two"), "unique_pointer": "ptr-2"},
                {"content": _encode("doc three"), "unique_pointer": "ptr-3"},
            ],
        )
        result = await c.get_file_contents(["ptr-1", "ptr-2", "ptr-3"])
        self.assertEqual(len(result), 3)

    async def test_missing_content_returns_empty_list(self) -> None:
        """Returns [] and logs warning when content field is missing."""
        c = _make_connector()
        _mock_response(c.client, [{"unique_pointer": GITLAB_POINTER}])  # no "content"
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()

    async def test_invalid_base64_returns_empty_list(self) -> None:
        """Returns [] and logs warning when base64 decoding fails."""
        c = _make_connector()
        _mock_response(c.client, [{"content": "!!!not-valid-base64!!!", "unique_pointer": GITLAB_POINTER}])
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()

    async def test_http_status_error_returns_empty_list(self) -> None:
        """Returns [] and logs warning on HTTPStatusError."""
        c = _make_connector()
        _mock_error(c.client, httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock()))
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()

    async def test_timeout_returns_empty_list(self) -> None:
        """Returns [] and logs warning on TimeoutException."""
        c = _make_connector()
        _mock_error(c.client, httpx.TimeoutException("timed out"))
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()

    async def test_connect_error_returns_empty_list(self) -> None:
        """Returns [] and logs warning on ConnectError."""
        c = _make_connector()
        _mock_error(c.client, httpx.ConnectError("connection refused"))
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()

    async def test_value_error_returns_empty_list(self) -> None:
        """Returns [] and logs warning on ValueError (e.g. bad JSON)."""
        c = _make_connector()
        _mock_error(c.client, ValueError("bad value"))
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_contents([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()


# ---------------------------------------------------------------------------
# get_file_metadata
# ---------------------------------------------------------------------------


class TestGetFileMetadata(unittest.IsolatedAsyncioTestCase):
    """Tests for Connector.get_file_metadata."""

    async def test_returns_list_of_dicts(self) -> None:
        """Returns the raw list of metadata dicts on success."""
        c = _make_connector()
        metadata = [{"unique_pointer": GITLAB_POINTER, "last_edit_date": "2026-01-01"}]
        _mock_response(c.client, metadata)
        result = await c.get_file_metadata([GITLAB_POINTER])
        self.assertEqual(result, metadata)

    async def test_posts_to_correct_url(self) -> None:
        """Posts to <url>/get_files."""
        c = _make_connector(url="http://connector")
        _mock_response(c.client, [])
        await c.get_file_metadata([GITLAB_POINTER])
        called_url = c.client.post.call_args[0][0]
        self.assertEqual(called_url, "http://connector/get_files")

    async def test_include_content_param_is_false(self) -> None:
        """Request params include include_content=False."""
        c = _make_connector()
        _mock_response(c.client, [])
        await c.get_file_metadata([GITLAB_POINTER])
        params = c.client.post.call_args[1]["params"]
        self.assertIn(("include_content", False), params)

    async def test_include_last_edit_date_param_is_true(self) -> None:
        """Request params include include_last_edit_date=True."""
        c = _make_connector()
        _mock_response(c.client, [])
        await c.get_file_metadata([GITLAB_POINTER])
        params = c.client.post.call_args[1]["params"]
        self.assertIn(("include_last_edit_date", True), params)

    async def test_pointers_sent_in_payload(self) -> None:
        """file_pointers are sent in the JSON body."""
        c = _make_connector()
        _mock_response(c.client, [])
        pointers = [GITLAB_POINTER]
        await c.get_file_metadata(pointers)
        payload = c.client.post.call_args[1]["json"]
        self.assertEqual(payload["file_pointers"], pointers)

    async def test_http_status_error_returns_empty_list(self) -> None:
        """Returns [] and logs warning on HTTPStatusError."""
        c = _make_connector()
        _mock_error(c.client, httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock()))
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_metadata([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()

    async def test_timeout_returns_empty_list(self) -> None:
        """Returns [] and logs warning on TimeoutException."""
        c = _make_connector()
        _mock_error(c.client, httpx.TimeoutException("timed out"))
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_metadata([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()

    async def test_connect_error_returns_empty_list(self) -> None:
        """Returns [] and logs warning on ConnectError."""
        c = _make_connector()
        _mock_error(c.client, httpx.ConnectError("connection refused"))
        with unittest.mock.patch("gateway.services.connector.dms_warning") as mock_warn:
            result = await c.get_file_metadata([GITLAB_POINTER])
        self.assertEqual(result, [])
        mock_warn.assert_called_once()

    async def test_multiple_pointers_return_all_metadata(self) -> None:
        """Returns one metadata dict per pointer."""
        c = _make_connector()
        metadata = [
            {"unique_pointer": "ptr-1", "last_edit_date": "2026-01-01"},
            {"unique_pointer": "ptr-2", "last_edit_date": "2026-01-02"},
        ]
        _mock_response(c.client, metadata)
        result = await c.get_file_metadata(["ptr-1", "ptr-2"])
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
