"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the gateway connector service.
"""

# Tests intentionally call private helpers on Connector for focused checks.
# pylint: disable=protected-access

import base64
import unittest
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from gateway.schemas import InputItem
from gateway.services.connector import Connector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GITLAB_POINTER = "https://gitlab.dms-lookup.com/api/v4/projects/7/repository/files/doc.txt"


def _encode(text: str) -> str:
    """Base64-encode a string as the connector would return it."""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def _make_mock_response(data: list[dict], status: int = 200) -> AsyncMock:
    """Build a mock aiohttp response used as an async context manager."""
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=data)
    mock_resp.status = status

    # Support `async with session.post(...) as response:`
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_connector_with_session(session: MagicMock) -> Connector:
    """
    Instantiate a Connector, bypassing __init__ env-var read, and inject a
    mock aiohttp.ClientSession.
    """
    with patch("gateway.services.connector.read_env_variable", return_value="http://connector"):
        c = Connector()
    c.session = session
    return c


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConnectorInit(unittest.TestCase):
    """Tests for Connector.__init__."""

    def test_url_strips_trailing_slash(self) -> None:
        with patch("gateway.services.connector.read_env_variable", return_value="http://connector/"):
            c = Connector()
        self.assertEqual(c.url, "http://connector")

    def test_url_without_trailing_slash(self) -> None:
        with patch("gateway.services.connector.read_env_variable", return_value="http://connector"):
            c = Connector()
        self.assertEqual(c.url, "http://connector")

    def test_timeout_class_constant(self) -> None:
        self.assertEqual(Connector.TIMEOUT, 120)

    def test_read_env_variable_is_called(self) -> None:
        with patch("gateway.services.connector.read_env_variable", return_value="http://x") as mock_env:
            Connector()
        mock_env.assert_called_once_with("STOCHAN_CONGATEWAY_URL")


# ---------------------------------------------------------------------------
# init / close
# ---------------------------------------------------------------------------


class TestConnectorLifecycle(unittest.IsolatedAsyncioTestCase):
    """Tests for Connector.init and Connector.close."""

    async def test_init_creates_client_session(self) -> None:
        with patch("gateway.services.connector.read_env_variable", return_value="http://connector"):
            c = Connector()
        with patch("aiohttp.ClientSession") as mock_cls:
            await c.init()
        mock_cls.assert_called_once()

    async def test_close_closes_session(self) -> None:
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        c = _make_connector_with_session(mock_session)
        await c.close()
        mock_session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_file_contents
# ---------------------------------------------------------------------------


class TestGetFileContents(unittest.IsolatedAsyncioTestCase):
    """Tests for Connector.get_file_contents."""

    async def test_returns_input_items(self) -> None:
        """Returns a list of InputItem on success."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response(
            [{"content": _encode("hello world"), "unique_pointer": GITLAB_POINTER}]
        )
        c = _make_connector_with_session(mock_session)
        result = await c.get_file_contents([GITLAB_POINTER], authorization=None)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], InputItem)

    async def test_decoded_content_is_correct(self) -> None:
        """Decoded content matches the original text."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response(
            [{"content": _encode("Top secret data."), "unique_pointer": GITLAB_POINTER}]
        )
        c = _make_connector_with_session(mock_session)
        result = await c.get_file_contents([GITLAB_POINTER], authorization=None)
        self.assertIn("Top secret data.", result[0].content)

    async def test_pointer_stored_in_metadata(self) -> None:
        """unique_pointer from response is stored in item metadata."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"content": _encode("content"), "unique_pointer": GITLAB_POINTER}])
        c = _make_connector_with_session(mock_session)
        result = await c.get_file_contents([GITLAB_POINTER], authorization=None)
        self.assertEqual(result[0].metadata.unique_pointer, GITLAB_POINTER)

    async def test_posts_to_correct_url(self) -> None:
        """Posts to <url>/get_files."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        c = _make_connector_with_session(mock_session)
        await c.get_file_contents([GITLAB_POINTER], authorization=None)
        called_url = mock_session.post.call_args[0][0]
        self.assertEqual(called_url, "http://connector/get_files")

    async def test_include_content_param_is_true(self) -> None:
        """Request params include include_content=true."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        c = _make_connector_with_session(mock_session)
        await c.get_file_contents([GITLAB_POINTER], authorization=None)
        params = mock_session.post.call_args[1]["params"]
        self.assertEqual(params.get("include_content"), "true")

    async def test_pointers_sent_in_payload(self) -> None:
        """file_pointers are sent in the JSON body."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        c = _make_connector_with_session(mock_session)
        pointers = [GITLAB_POINTER]
        await c.get_file_contents(pointers, authorization=None)
        payload = mock_session.post.call_args[1]["json"]
        self.assertEqual(payload["file_pointers"], pointers)

    async def test_authorization_header_sent_when_provided(self) -> None:
        """Authorization header is included when a token is passed."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        c = _make_connector_with_session(mock_session)
        await c.get_file_contents([GITLAB_POINTER], authorization="Bearer tok123")
        headers = mock_session.post.call_args[1]["headers"]
        self.assertIn(("Authorization", "Bearer tok123"), headers)

    async def test_no_authorization_header_when_none(self) -> None:
        """No Authorization header is sent when authorization is None."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"content": _encode("data"), "unique_pointer": GITLAB_POINTER}])
        c = _make_connector_with_session(mock_session)
        await c.get_file_contents([GITLAB_POINTER], authorization=None)
        headers = mock_session.post.call_args[1]["headers"]
        self.assertIsNone(headers)

    async def test_multiple_pointers_return_multiple_items(self) -> None:
        """One InputItem is returned per valid pointer."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response(
            [
                {"content": _encode("doc one"), "unique_pointer": "ptr-1"},
                {"content": _encode("doc two"), "unique_pointer": "ptr-2"},
                {"content": _encode("doc three"), "unique_pointer": "ptr-3"},
            ]
        )
        c = _make_connector_with_session(mock_session)
        result = await c.get_file_contents(["ptr-1", "ptr-2", "ptr-3"], authorization=None)
        self.assertEqual(len(result), 3)

    async def test_missing_pointer_skips_entry(self) -> None:
        """Entry without unique_pointer is skipped (no crash)."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"content": _encode("data")}])  # no unique_pointer
        c = _make_connector_with_session(mock_session)
        with patch("gateway.services.connector.dms_warning"):
            result = await c.get_file_contents([GITLAB_POINTER], authorization=None)
        self.assertEqual(result, [])

    async def test_missing_pointer_logs_warning(self) -> None:
        """Entry without unique_pointer logs a dms_warning."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"content": _encode("data")}])
        c = _make_connector_with_session(mock_session)
        with patch("gateway.services.connector.dms_warning") as mock_warn:
            await c.get_file_contents([GITLAB_POINTER], authorization=None)
        mock_warn.assert_called_once()

    async def test_invalid_base64_entry_is_skipped(self) -> None:
        """Entry with invalid base64 content is skipped (returns None from _extract_text)."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response(
            [{"content": "!!!not-valid-base64!!!", "unique_pointer": GITLAB_POINTER}]
        )
        c = _make_connector_with_session(mock_session)
        with patch("gateway.services.connector.dms_warning"):
            result = await c.get_file_contents([GITLAB_POINTER], authorization=None)
        self.assertEqual(result, [])

    async def test_missing_content_field_is_skipped(self) -> None:
        """Entry with no content field is skipped (_extract_text receives None)."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.return_value = _make_mock_response([{"unique_pointer": GITLAB_POINTER}])
        c = _make_connector_with_session(mock_session)
        result = await c.get_file_contents([GITLAB_POINTER], authorization=None)
        self.assertEqual(result, [])

    async def test_client_error_raises(self) -> None:
        """aiohttp.ClientError propagates from get_file_contents."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.side_effect = aiohttp.ClientError("connection refused")
        c = _make_connector_with_session(mock_session)
        with patch("gateway.services.connector.dms_warning"):
            with self.assertRaises(aiohttp.ClientError):
                await c.get_file_contents([GITLAB_POINTER], authorization=None)

    async def test_client_error_logs_warning(self) -> None:
        """dms_warning is called on aiohttp.ClientError."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.side_effect = aiohttp.ClientError("err")
        c = _make_connector_with_session(mock_session)
        with patch("gateway.services.connector.dms_warning") as mock_warn:
            with self.assertRaises(aiohttp.ClientError):
                await c.get_file_contents([GITLAB_POINTER], authorization=None)
        mock_warn.assert_called_once()

    async def test_timeout_error_raises(self) -> None:
        """TimeoutError propagates from get_file_contents."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.side_effect = TimeoutError("timed out")
        c = _make_connector_with_session(mock_session)
        with patch("gateway.services.connector.dms_warning"):
            with self.assertRaises(TimeoutError):
                await c.get_file_contents([GITLAB_POINTER], authorization=None)

    async def test_value_error_raises(self) -> None:
        """ValueError (e.g. bad JSON) propagates from get_file_contents."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.post.side_effect = ValueError("bad json")
        c = _make_connector_with_session(mock_session)
        with patch("gateway.services.connector.dms_warning"):
            with self.assertRaises(ValueError):
                await c.get_file_contents([GITLAB_POINTER], authorization=None)


# ---------------------------------------------------------------------------
# _extract_text (static method)
# ---------------------------------------------------------------------------


class TestExtractText(unittest.TestCase):
    """Tests for Connector._extract_text."""

    def test_none_input_returns_none(self) -> None:
        result = Connector._extract_text(None)
        self.assertIsNone(result)

    def test_valid_utf8_text_is_returned(self) -> None:
        encoded = _encode("plain text content")
        result = Connector._extract_text(encoded)
        self.assertIsNotNone(result)
        self.assertIn("plain text content", result)

    def test_invalid_base64_returns_none(self) -> None:
        with patch("gateway.services.connector.dms_warning"):
            result = Connector._extract_text("!!!not-valid-base64!!!")
        self.assertIsNone(result)

    def test_invalid_base64_logs_warning(self) -> None:
        with patch("gateway.services.connector.dms_warning") as mock_warn:
            Connector._extract_text("!!!not-valid-base64!!!")
        mock_warn.assert_called_once()

    def test_non_utf8_binary_returns_none(self) -> None:
        """Bytes that are not valid UTF-8 and not markitdown-convertible return None."""
        raw = bytes([0xFF, 0xFE, 0x00, 0x01])  # not valid UTF-8
        encoded = base64.b64encode(raw).decode("utf-8")
        with patch("gateway.services.connector.dms_warning"):
            result = Connector._extract_text(encoded)
        self.assertIsNone(result)

    def test_non_utf8_binary_logs_warning(self) -> None:
        raw = bytes([0xFF, 0xFE, 0x00, 0x01])
        encoded = base64.b64encode(raw).decode("utf-8")
        with patch("gateway.services.connector.dms_warning") as mock_warn:
            Connector._extract_text(encoded)
        mock_warn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
