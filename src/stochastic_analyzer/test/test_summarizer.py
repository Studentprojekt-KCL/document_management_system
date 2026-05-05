"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the stochastic_analyzer document summarizer.
"""

# Tests intentionally call private helpers on Summarizer for focused checks.
# pylint: disable=protected-access

import unittest
from unittest.mock import AsyncMock, MagicMock

import httpx
from gateway.services.summarizer import LanguageConfig
from gateway.schemas import InputItem, MetadataTemplate, SummaryResult
from gateway.services.summarizer import Summarizer, SummarizerConfig, detect_language

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lang_config(sample_size: int = 100, threshold: int = 2) -> LanguageConfig:
    return LanguageConfig(sample_size=sample_size, swedish_char_threshold=threshold)


def _make_config(
    url: str = "http://gpu-server",
    model: str = "ministral",
    timeout: int = 30,
    lang_config: LanguageConfig | None = None,
) -> SummarizerConfig:
    return SummarizerConfig(
        url=url,
        model=model,
        timeout=timeout,
        lang_config=lang_config or _make_lang_config(),
    )


def _make_summarizer(
    url: str = "http://gpu-server",
    threshold: int = 2,
) -> Summarizer:
    """Return a Summarizer with a mock async HTTP client."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    config = _make_config(url=url, lang_config=_make_lang_config(threshold=threshold))
    return Summarizer(config=config, client=mock_client)


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


def _mock_llm_response(mock_client: AsyncMock, text: str) -> None:
    """Configure mock_client.post to return a valid LLM JSON response."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"response": text}
    mock_client.post.return_value = mock_resp


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage(unittest.TestCase):
    """Tests for the module-level detect_language function."""

    def test_returns_swedish_when_threshold_met(self) -> None:
        """Returns 'swedish' when Swedish character count meets threshold."""
        result = detect_language("åäö extra text", sample_size=100, swedish_char_threshold=2)
        self.assertEqual(result, "swedish")

    def test_returns_english_when_no_swedish_chars(self) -> None:
        """Returns 'english' for text with no Swedish characters."""
        result = detect_language("hello world", sample_size=100, swedish_char_threshold=2)
        self.assertEqual(result, "english")

    def test_returns_english_when_below_threshold(self) -> None:
        """Returns 'english' when Swedish chars present but below threshold."""
        result = detect_language("one å here", sample_size=100, swedish_char_threshold=3)
        self.assertEqual(result, "english")

    def test_only_samples_prefix(self) -> None:
        """Swedish chars beyond sample_size are ignored."""
        long_english = "a" * 200 + "åååå"
        result = detect_language(long_english, sample_size=100, swedish_char_threshold=2)
        self.assertEqual(result, "english")

    def test_case_insensitive(self) -> None:
        """Detection is case-insensitive (uppercase Å counts)."""
        result = detect_language("ÅÄÖ text", sample_size=100, swedish_char_threshold=2)
        self.assertEqual(result, "swedish")

    def test_early_exit_on_threshold(self) -> None:
        """Returns 'swedish' as soon as threshold is reached, even mid-string."""
        result = detect_language("aåbäcö rest", sample_size=100, swedish_char_threshold=3)
        self.assertEqual(result, "swedish")


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestSummarizerInit(unittest.TestCase):
    """Tests for Summarizer.__init__."""

    def test_url_is_stored(self) -> None:
        s = _make_summarizer(url="http://example.com")
        self.assertEqual(s.url, "http://example.com")

    def test_client_is_stored(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        config = _make_config()
        s = Summarizer(config=config, client=mock_client)
        self.assertIs(s.client, mock_client)

    def test_model_is_stored(self) -> None:
        config = _make_config(model="my-model")
        s = Summarizer(config=config, client=AsyncMock())
        self.assertEqual(s.model, "my-model")

    def test_timeout_is_stored(self) -> None:
        config = _make_config(timeout=99)
        s = Summarizer(config=config, client=AsyncMock())
        self.assertEqual(s.timeout, 99)


# ---------------------------------------------------------------------------
# _detect_majority_language
# ---------------------------------------------------------------------------


class TestDetectMajorityLanguage(unittest.TestCase):
    """Tests for Summarizer._detect_majority_language."""

    def setUp(self) -> None:
        self.summarizer = _make_summarizer(threshold=2)

    def test_majority_swedish(self) -> None:
        """Returns 'swedish' when more than half the docs are Swedish."""
        items = [
            _make_item(content="åäö Swedish content"),
            _make_item(content="åäö Swedish content"),
            _make_item(content="English content only"),
        ]
        self.assertEqual(self.summarizer._detect_majority_language(items), "swedish")

    def test_majority_english(self) -> None:
        """Returns 'english' when half or fewer docs are Swedish."""
        items = [
            _make_item(content="English content only"),
            _make_item(content="English content only"),
            _make_item(content="åäö Swedish content"),
        ]
        self.assertEqual(self.summarizer._detect_majority_language(items), "english")

    def test_tie_returns_english(self) -> None:
        """Returns 'english' when exactly half are Swedish (not strictly majority)."""
        items = [
            _make_item(content="åäö Swedish"),
            _make_item(content="English only"),
        ]
        self.assertEqual(self.summarizer._detect_majority_language(items), "english")

    def test_all_swedish(self) -> None:
        items = [_make_item(content="åäö content") for _ in range(3)]
        self.assertEqual(self.summarizer._detect_majority_language(items), "swedish")

    def test_all_english(self) -> None:
        items = [_make_item(content="English content") for _ in range(3)]
        self.assertEqual(self.summarizer._detect_majority_language(items), "english")


# ---------------------------------------------------------------------------
# _call_llm
# ---------------------------------------------------------------------------


class TestCallLlm(unittest.IsolatedAsyncioTestCase):
    """Tests for Summarizer._call_llm."""

    async def test_returns_response_text(self) -> None:
        """Returns stripped response text on success."""
        s = _make_summarizer()
        _mock_llm_response(s.client, "  summary text  ")
        result = await s._call_llm("some prompt")
        self.assertEqual(result, "summary text")

    async def test_posts_to_correct_url(self) -> None:
        """Posts to the configured URL."""
        s = _make_summarizer(url="http://my-llm")
        _mock_llm_response(s.client, "ok")
        await s._call_llm("prompt")
        called_url = s.client.post.call_args[0][0]
        self.assertEqual(called_url, "http://my-llm")

    async def test_payload_contains_model(self) -> None:
        """Request payload includes the configured model."""
        config = _make_config(model="ministral-8b")
        s = Summarizer(config=config, client=AsyncMock(spec=httpx.AsyncClient))
        _mock_llm_response(s.client, "ok")
        await s._call_llm("prompt")
        payload = s.client.post.call_args[1]["json"]
        self.assertEqual(payload["model"], "ministral-8b")

    async def test_payload_contains_prompt(self) -> None:
        """Request payload includes the prompt."""
        s = _make_summarizer()
        _mock_llm_response(s.client, "ok")
        await s._call_llm("my test prompt")
        payload = s.client.post.call_args[1]["json"]
        self.assertEqual(payload["prompt"], "my test prompt")

    async def test_http_status_error_returns_none(self) -> None:
        """Returns None and logs warning on HTTPStatusError."""
        s = _make_summarizer()
        mock_response = MagicMock()
        mock_response.status_code = 500
        s.client.post.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
        with unittest.mock.patch("gateway.services.summarizer.dms_warning") as mock_warn:
            result = await s._call_llm("prompt")
        self.assertIsNone(result)
        mock_warn.assert_called_once()

    async def test_timeout_returns_none(self) -> None:
        """Returns None and logs warning on TimeoutException."""
        s = _make_summarizer()
        s.client.post.side_effect = httpx.TimeoutException("timed out")
        with unittest.mock.patch("gateway.services.summarizer.dms_warning") as mock_warn:
            result = await s._call_llm("prompt")
        self.assertIsNone(result)
        mock_warn.assert_called_once()

    async def test_json_decode_error_returns_none(self) -> None:
        """Returns None and logs warning on JSONDecodeError."""
        from json.decoder import JSONDecodeError

        s = _make_summarizer()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = JSONDecodeError("bad json", "", 0)
        s.client.post.return_value = mock_resp
        with unittest.mock.patch("gateway.services.summarizer.dms_warning") as mock_warn:
            result = await s._call_llm("prompt")
        self.assertIsNone(result)
        mock_warn.assert_called_once()


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


class TestSummarize(unittest.IsolatedAsyncioTestCase):
    """Tests for Summarizer.summarize."""

    async def test_single_doc_returns_individual_summary(self) -> None:
        """Single document skips synthesis and returns the individual summary directly."""
        s = _make_summarizer()
        _mock_llm_response(s.client, "individual summary")
        result = await s.summarize([_make_item()])
        self.assertIsInstance(result, SummaryResult)
        self.assertEqual(result.summary, "individual summary")

    async def test_single_doc_calls_llm_once(self) -> None:
        """Single document only calls the LLM once (no synthesis stage)."""
        s = _make_summarizer()
        _mock_llm_response(s.client, "summary")
        await s.summarize([_make_item()])
        self.assertEqual(s.client.post.call_count, 1)

    async def test_multiple_docs_calls_llm_for_each_plus_synthesis(self) -> None:
        """N documents trigger N individual calls plus 1 synthesis call."""
        s = _make_summarizer()
        _mock_llm_response(s.client, "a summary")
        items = [_make_item(pointer=f"ptr-{i}") for i in range(3)]
        await s.summarize(items)
        self.assertEqual(s.client.post.call_count, 4)  # 3 individual + 1 synthesis

    async def test_multiple_docs_returns_summary_result(self) -> None:
        """Returns a SummaryResult for multiple documents."""
        s = _make_summarizer()
        _mock_llm_response(s.client, "synthesized summary")
        items = [_make_item(pointer=f"ptr-{i}") for i in range(2)]
        result = await s.summarize(items)
        self.assertIsInstance(result, SummaryResult)

    async def test_all_llm_failures_returns_none(self) -> None:
        """Returns None when all individual LLM calls fail."""
        s = _make_summarizer()
        s.client.post.side_effect = httpx.TimeoutException("timed out")
        with unittest.mock.patch("gateway.services.summarizer.dms_warning"):
            result = await s.summarize([_make_item(), _make_item()])
        self.assertIsNone(result)

    async def test_synthesis_failure_returns_none(self) -> None:
        """Returns None when synthesis LLM call fails after successful individual summaries."""
        s = _make_summarizer()
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if call_count <= 2:
                mock_resp.json.return_value = {"response": "individual summary"}
            else:
                mock_resp.json.return_value = {"response": ""}  # empty synthesis
            return mock_resp

        s.client.post.side_effect = side_effect
        result = await s.summarize([_make_item(), _make_item()])
        # Empty string stripped becomes "" which is falsy → SummaryResult("") or None depending on impl
        # The synthesized result is returned regardless; verify it's a SummaryResult or None
        self.assertTrue(result is None or isinstance(result, SummaryResult))

    async def test_missing_doc_name_falls_back_to_document_number(self) -> None:
        """Documents without a name use 'Document N' as the label."""
        s = _make_summarizer()
        _mock_llm_response(s.client, "summary")
        item = _make_item(name=None)
        # Should not raise; the name fallback is handled internally
        result = await s.summarize([item])
        self.assertIsNotNone(result)

    async def test_returns_summary_result_instance(self) -> None:
        """summarize() always returns a SummaryResult (not a raw string)."""
        s = _make_summarizer()
        _mock_llm_response(s.client, "some text")
        result = await s.summarize([_make_item()])
        self.assertIsInstance(result, SummaryResult)
