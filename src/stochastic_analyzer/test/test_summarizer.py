"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the stochastic_analyzer document summarizer.
"""

# Tests intentionally call private helpers on Summarizer for focused checks.
# pylint: disable=protected-access

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from gateway.services.summarize import Summarizer
from gateway.schemas import InputItem, MetadataTemplate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(
    content: str = "Some document content.",
    name: str | None = "doc.pdf",
    author: str | None = "Ali",
    pointer: str | None = "ptr-001",
) -> InputItem:
    return InputItem(
        content=content,
        metadata=MetadataTemplate(name=name, author=author, unique_pointer=pointer),
    )


def _make_summarizer() -> Summarizer:
    """Return a Summarizer with env vars patched and a mock aiohttp session."""
    with (patch("gateway.services.summarize.read_env_variable", side_effect=_fake_env),):
        s = Summarizer()
    s.session = _make_mock_session("default summary")
    return s


def _fake_env(key: str) -> str:
    return {"STOCHAN_LLM_URL": "http://gpu-server", "STOCHAN_LLM_MODEL": "ministral-3:14B"}[key]


def _make_mock_session(response_text: str) -> MagicMock:
    """Return a mock aiohttp.ClientSession whose post() returns response_text."""
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value={"response": response_text})

    # aiohttp uses async context manager for session.post(...)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.post = MagicMock(return_value=mock_cm)
    return session


def _make_session_with_side_effect(side_effect) -> MagicMock:
    """Return a session whose post() raises side_effect."""
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=side_effect)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.post = MagicMock(return_value=mock_cm)
    return session


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestSummarizerInit(unittest.TestCase):
    """Tests for Summarizer.__init__."""

    def test_url_is_stored(self) -> None:
        with patch("gateway.services.summarize.read_env_variable", side_effect=_fake_env):
            s = Summarizer()
        self.assertEqual(s.url, "http://gpu-server")

    def test_url_trailing_slash_stripped(self) -> None:
        def env_with_slash(key: str) -> str:
            return {"STOCHAN_LLM_URL": "http://gpu-server/", "STOCHAN_LLM_MODEL": "model"}[key]

        with patch("gateway.services.summarize.read_env_variable", side_effect=env_with_slash):
            s = Summarizer()
        self.assertEqual(s.url, "http://gpu-server")

    def test_model_is_stored(self) -> None:
        with patch("gateway.services.summarize.read_env_variable", side_effect=_fake_env):
            s = Summarizer()
        self.assertEqual(s.model, "ministral-3:14B")

    def test_timeout_constant(self) -> None:
        self.assertEqual(Summarizer.TIMEOUT, 120)

    def test_max_combined_chars_constant(self) -> None:
        self.assertEqual(Summarizer.MAX_COMBINED_CHARS, 200_000)


# ---------------------------------------------------------------------------
# _call_llm
# ---------------------------------------------------------------------------


class TestCallLlm(unittest.IsolatedAsyncioTestCase):
    """Tests for Summarizer._call_llm."""

    async def test_returns_stripped_response_text(self) -> None:
        s = _make_summarizer()
        s.session = _make_mock_session("  summary text  ")
        result = await s._call_llm("some prompt")
        self.assertEqual(result, "summary text")

    async def test_posts_to_configured_url(self) -> None:
        s = _make_summarizer()
        await s._call_llm("prompt")
        called_url = s.session.post.call_args[0][0]
        self.assertEqual(called_url, "http://gpu-server")

    async def test_payload_contains_model(self) -> None:
        s = _make_summarizer()
        await s._call_llm("prompt")
        payload = s.session.post.call_args[1]["json"]
        self.assertEqual(payload["model"], "ministral-3:14B")

    async def test_payload_contains_prompt(self) -> None:
        s = _make_summarizer()
        await s._call_llm("my test prompt")
        payload = s.session.post.call_args[1]["json"]
        self.assertEqual(payload["prompt"], "my test prompt")

    async def test_payload_stream_is_false(self) -> None:
        s = _make_summarizer()
        await s._call_llm("prompt")
        payload = s.session.post.call_args[1]["json"]
        self.assertFalse(payload["stream"])

    async def test_client_error_returns_none(self) -> None:
        s = _make_summarizer()
        s.session = _make_session_with_side_effect(aiohttp.ClientError("connection failed"))
        with patch("gateway.services.summarize.dms_warning") as mock_warn:
            result = await s._call_llm("prompt")
        self.assertIsNone(result)
        mock_warn.assert_called_once()

    async def test_timeout_returns_none(self) -> None:
        s = _make_summarizer()
        s.session = _make_session_with_side_effect(TimeoutError("timed out"))
        with patch("gateway.services.summarize.dms_warning") as mock_warn:
            result = await s._call_llm("prompt")
        self.assertIsNone(result)
        mock_warn.assert_called_once()

    async def test_value_error_returns_none(self) -> None:
        s = _make_summarizer()
        s.session = _make_session_with_side_effect(ValueError("bad value"))
        with patch("gateway.services.summarize.dms_warning") as mock_warn:
            result = await s._call_llm("prompt")
        self.assertIsNone(result)
        mock_warn.assert_called_once()

    async def test_non_dict_response_returns_none(self) -> None:
        """Returns None when the LLM response is not a dict."""
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(return_value=["not", "a", "dict"])
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        s = _make_summarizer()
        s.session.post = MagicMock(return_value=mock_cm)
        with patch("gateway.services.summarize.dms_warning") as mock_warn:
            result = await s._call_llm("prompt")
        self.assertIsNone(result)
        mock_warn.assert_called_once()

    async def test_empty_response_string_returns_none(self) -> None:
        """An empty (or whitespace-only) response string is treated as None."""
        s = _make_summarizer()
        s.session = _make_mock_session("   ")
        result = await s._call_llm("prompt")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


class TestSummarize(unittest.IsolatedAsyncioTestCase):
    """Tests for Summarizer.summarize."""

    async def test_empty_list_returns_empty_summary(self) -> None:
        """No items → returns {'summary': ''} with a warning."""
        s = _make_summarizer()
        with patch("gateway.services.summarize.dms_warning"):
            result = await s.summarize([])
        self.assertEqual(result, {"summary": ""})

    async def test_single_doc_returns_dict_with_summary(self) -> None:
        s = _make_summarizer()
        s.session = _make_mock_session("individual summary")
        result = await s.summarize([_make_item()])
        self.assertIsInstance(result, dict)
        self.assertEqual(result["summary"], "individual summary")

    async def test_single_doc_calls_llm_once(self) -> None:
        """Single document only calls the LLM once (no pipeline)."""
        s = _make_summarizer()
        await s.summarize([_make_item()])
        self.assertEqual(s.session.post.call_count, 1)

    async def test_single_doc_failure_returns_none(self) -> None:
        s = _make_summarizer()
        s.session = _make_session_with_side_effect(aiohttp.ClientError("fail"))
        with patch("gateway.services.summarize.dms_warning"):
            result = await s.summarize([_make_item()])
        self.assertIsNone(result)

    async def test_multiple_docs_returns_dict_with_summary(self) -> None:
        s = _make_summarizer()
        s.session = _make_mock_session("synthesized summary")
        items = [_make_item(pointer=f"ptr-{i}") for i in range(2)]
        result = await s.summarize(items)
        self.assertIsInstance(result, dict)
        self.assertIn("summary", result)

    async def test_multiple_docs_calls_llm_for_each_plus_synthesis(self) -> None:
        """N documents trigger N stage-1 calls plus 1 stage-2 synthesis call."""
        s = _make_summarizer()
        items = [_make_item(pointer=f"ptr-{i}") for i in range(3)]
        await s.summarize(items)
        self.assertEqual(s.session.post.call_count, 4)  # 3 stage-1 + 1 stage-2

    async def test_all_stage_one_failures_returns_none(self) -> None:
        """Returns None when every stage-1 LLM call fails."""
        s = _make_summarizer()
        s.session = _make_session_with_side_effect(aiohttp.ClientError("fail"))
        with patch("gateway.services.summarize.dms_warning"):
            result = await s.summarize([_make_item(), _make_item()])
        self.assertIsNone(result)

    async def test_stage_two_failure_returns_none(self) -> None:
        """Returns None when the stage-2 synthesis call fails."""
        s = _make_summarizer()
        call_count = 0

        async def alternating_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return {"response": "stage 1 summary"}
            return {"response": ""}  # empty → None after strip

        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(side_effect=alternating_response)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        s.session.post = MagicMock(return_value=mock_cm)

        result = await s.summarize([_make_item(), _make_item()])
        self.assertIsNone(result)

    async def test_combined_too_long_returns_empty_summary(self) -> None:
        """Returns {'summary': ''} when combined stage-1 output exceeds MAX_COMBINED_CHARS."""
        s = _make_summarizer()
        # Each stage-1 response is just over half the limit so combined exceeds it
        big_text = "x" * (Summarizer.MAX_COMBINED_CHARS // 2 + 1)
        s.session = _make_mock_session(big_text)
        items = [_make_item(pointer=f"ptr-{i}") for i in range(2)]
        with patch("gateway.services.summarize.dms_warning"):
            result = await s.summarize(items)
        self.assertEqual(result, {"summary": ""})


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


class TestMerge(unittest.IsolatedAsyncioTestCase):
    """Tests for Summarizer.merge."""

    async def test_merge_returns_dict_with_summary(self) -> None:
        s = _make_summarizer()
        s.session = _make_mock_session("merged document")
        items = [_make_item(pointer=f"ptr-{i}") for i in range(2)]
        result = await s.merge(items)
        self.assertIsInstance(result, dict)
        self.assertIn("summary", result)

    async def test_merge_calls_pipeline(self) -> None:
        """merge() goes through the two-stage pipeline (N+1 LLM calls)."""
        s = _make_summarizer()
        items = [_make_item(pointer=f"ptr-{i}") for i in range(2)]
        await s.merge(items)
        self.assertEqual(s.session.post.call_count, 3)  # 2 stage-1 + 1 stage-2

    async def test_merge_failure_returns_none(self) -> None:
        s = _make_summarizer()
        s.session = _make_session_with_side_effect(aiohttp.ClientError("fail"))
        with patch("gateway.services.summarize.dms_warning"):
            result = await s.merge([_make_item(), _make_item()])
        self.assertIsNone(result)
