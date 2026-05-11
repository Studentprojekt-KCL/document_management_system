"""Unit tests for gateway/services/merger.py"""

from json.decoder import JSONDecodeError
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gateway.services.merger import Merger, MergerConfig
from gateway.services.summarizer import LanguageConfig
from gateway.schemas import InputItem, SummaryResult

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_config(
    url: str = "http://llm/api/generate",
    model: str = "ministral",
    timeout: int = 30,
    sample_size: int = 200,
    swedish_char_threshold: int = 3,
) -> MergerConfig:
    return MergerConfig(
        url=url,
        model=model,
        timeout=timeout,
        lang_config=LanguageConfig(
            sample_size=sample_size,
            swedish_char_threshold=swedish_char_threshold,
        ),
    )


def make_input_item(content: str, name: str | None = None) -> InputItem:
    """Construct an InputItem bypassing Pydantic validation.

    MetadataTemplate is a Pydantic model; using model_construct avoids the
    need to know every required field while keeping the .name attribute that
    merger.py accesses at runtime.
    """
    from gateway.schemas import MetadataTemplate

    metadata = MetadataTemplate.model_construct(name=name)
    return InputItem.model_construct(content=content, metadata=metadata)


def make_merger(config: MergerConfig | None = None, client: httpx.AsyncClient | None = None) -> Merger:
    config = config or make_config()
    client = client or AsyncMock(spec=httpx.AsyncClient)
    return Merger(config=config, client=client)


def _ok_response(text: str) -> MagicMock:
    """Build a mock httpx response that looks like a successful LLM reply."""
    resp = MagicMock(spec=httpx.Response)
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"response": text}
    return resp


# ---------------------------------------------------------------------------
# MergerConfig
# ---------------------------------------------------------------------------


class TestMergerConfig:
    def test_fields_are_stored(self):
        lang_cfg = LanguageConfig(sample_size=100, swedish_char_threshold=2)
        cfg = MergerConfig(url="http://x", model="m", timeout=10, lang_config=lang_cfg)
        assert cfg.url == "http://x"
        assert cfg.model == "m"
        assert cfg.timeout == 10
        assert cfg.lang_config is lang_cfg


# ---------------------------------------------------------------------------
# Merger.__init__
# ---------------------------------------------------------------------------


class TestMergerInit:
    def test_attributes_are_set_from_config(self):
        cfg = make_config(url="http://a", model="llm-x", timeout=99)
        client = AsyncMock(spec=httpx.AsyncClient)
        merger = Merger(config=cfg, client=client)

        assert merger.url == "http://a"
        assert merger.model == "llm-x"
        assert merger.timeout == 99
        assert merger.client is client
        assert merger.lang_config is cfg.lang_config


# ---------------------------------------------------------------------------
# Merger.from_env
# ---------------------------------------------------------------------------


class TestMergerFromEnv:
    def test_constructs_from_env_vars(self):
        env_values = {
            "STOCHAN_LLM_URL": "http://env-url",
            "STOCHAN_LLM_MODEL": "env-model",
            "STOCHAN_LLM_TIMEOUT": 45,
            "STOCHAN_SAMPLE_SIZE": 150,
            "STOCHAN_SWEDISH_CHAR_THRESHOLD": 4,
        }

        client = AsyncMock(spec=httpx.AsyncClient)

        with (
            patch("gateway.services.merger.read_env_variable", side_effect=lambda k: env_values[k]),
            patch("gateway.services.merger.read_int_env_variable", side_effect=lambda k: env_values[k]),
        ):
            merger = Merger.from_env(client)

        assert merger.url == "http://env-url"
        assert merger.model == "env-model"
        assert merger.timeout == 45
        assert merger.lang_config.sample_size == 150
        assert merger.lang_config.swedish_char_threshold == 4
        assert merger.client is client


# ---------------------------------------------------------------------------
# Merger._call_llm
# ---------------------------------------------------------------------------


class TestCallLlm:
    @pytest.mark.anyio
    async def test_returns_stripped_response_text(self):
        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(return_value=_ok_response("  merged doc  "))
        merger = make_merger(client=client)

        result = await merger._call_llm("some prompt")

        assert result == "merged doc"

    @pytest.mark.anyio
    async def test_sends_correct_payload(self):
        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(return_value=_ok_response("ok"))
        cfg = make_config(url="http://llm/gen", model="model-x", timeout=20)
        merger = make_merger(config=cfg, client=client)

        with patch("gateway.services.merger.MERGER_SYSTEM_PROMPT", "sys-prompt"):
            await merger._call_llm("hello prompt")

        client.post.assert_awaited_once()
        _, kwargs = client.post.call_args
        payload = kwargs["json"]
        assert payload["model"] == "model-x"
        assert payload["prompt"] == "hello prompt"
        assert payload["system"] == "sys-prompt"
        assert payload["stream"] is False
        assert kwargs["timeout"] == 20

    @pytest.mark.anyio
    async def test_returns_none_on_http_status_error(self):
        client = AsyncMock(spec=httpx.AsyncClient)
        error_response = MagicMock(spec=httpx.Response)
        error_response.status_code = 500
        client.post = AsyncMock(side_effect=httpx.HTTPStatusError("server error", request=MagicMock(), response=error_response))
        merger = make_merger(client=client)

        with patch("gateway.services.merger.dms_warning") as mock_warn:
            result = await merger._call_llm("prompt")

        assert result is None
        mock_warn.assert_called_once()
        assert "500" in mock_warn.call_args[0][0]

    @pytest.mark.anyio
    async def test_returns_none_on_json_decode_error(self):
        resp = MagicMock(spec=httpx.Response)
        resp.raise_for_status = MagicMock()
        resp.json.side_effect = JSONDecodeError("bad json", "", 0)
        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(return_value=resp)
        merger = make_merger(client=client)

        with patch("gateway.services.merger.dms_warning") as mock_warn:
            result = await merger._call_llm("prompt")

        assert result is None
        mock_warn.assert_called_once()

    @pytest.mark.anyio
    async def test_returns_none_on_timeout(self):
        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        merger = make_merger(client=client)

        with patch("gateway.services.merger.dms_warning") as mock_warn:
            result = await merger._call_llm("prompt")

        assert result is None
        mock_warn.assert_called_once()

    @pytest.mark.anyio
    async def test_returns_empty_string_when_response_key_missing(self):
        resp = MagicMock(spec=httpx.Response)
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {}  # no "response" key
        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(return_value=resp)
        merger = make_merger(client=client)

        result = await merger._call_llm("prompt")

        assert result == ""


# ---------------------------------------------------------------------------
# Merger._detect_majority_language
# ---------------------------------------------------------------------------


class TestDetectMajorityLanguage:
    def test_majority_swedish(self):
        merger = make_merger()
        items = [make_input_item("text") for _ in range(3)]
        with patch("gateway.services.merger.detect_language", return_value="swedish"):
            assert merger._detect_majority_language(items) == "swedish"

    def test_majority_english(self):
        merger = make_merger()
        items = [make_input_item("text") for _ in range(3)]
        with patch("gateway.services.merger.detect_language", return_value="english"):
            assert merger._detect_majority_language(items) == "english"

    def test_exactly_half_swedish_returns_english(self):
        """When swedish_count == len/2 (not strictly greater), result is english."""
        merger = make_merger()
        items = [make_input_item("x"), make_input_item("x")]
        langs = iter(["swedish", "english"])
        with patch("gateway.services.merger.detect_language", side_effect=lambda *_: next(langs)):
            result = merger._detect_majority_language(items)
        assert result == "english"

    def test_passes_lang_config_to_detect_language(self):
        cfg = make_config(sample_size=123, swedish_char_threshold=7)
        merger = make_merger(config=cfg)
        items = [make_input_item("hello")]

        with patch("gateway.services.merger.detect_language", return_value="english") as mock_detect:
            merger._detect_majority_language(items)

        mock_detect.assert_called_once_with("hello", 123, 7)

    def test_single_swedish_item(self):
        merger = make_merger()
        items = [make_input_item("hej")]
        with patch("gateway.services.merger.detect_language", return_value="swedish"):
            assert merger._detect_majority_language(items) == "swedish"


# ---------------------------------------------------------------------------
# Merger.merge
# ---------------------------------------------------------------------------

FAKE_MERGE_PROMPT = {
    "english": "Merge {doc_count} docs:\n{combined_documents}",
    "swedish": "Slå ihop {doc_count} dokument:\n{combined_documents}",
}


class TestMerge:
    @pytest.mark.anyio
    async def test_returns_summary_result_on_success(self):
        merger = make_merger()
        items = [make_input_item("Doc A content", name="A"), make_input_item("Doc B content", name="B")]

        with (
            patch("gateway.services.merger.detect_language", return_value="english"),
            patch("gateway.services.merger.MERGE_PROMPT", FAKE_MERGE_PROMPT),
            patch.object(merger, "_call_llm", new=AsyncMock(return_value="merged result")),
        ):
            result = await merger.merge(items)

        assert isinstance(result, SummaryResult)
        assert result.summary == "merged result"

    @pytest.mark.anyio
    async def test_returns_none_when_llm_fails(self):
        merger = make_merger()
        items = [make_input_item("content")]

        with (
            patch("gateway.services.merger.detect_language", return_value="english"),
            patch("gateway.services.merger.MERGE_PROMPT", FAKE_MERGE_PROMPT),
            patch.object(merger, "_call_llm", new=AsyncMock(return_value=None)),
        ):
            result = await merger.merge(items)

        assert result is None

    @pytest.mark.anyio
    async def test_prompt_includes_document_blocks(self):
        merger = make_merger()
        items = [
            make_input_item("alpha content", name="Alpha"),
            make_input_item("beta content", name="Beta"),
        ]
        captured_prompt = {}

        async def capture(prompt: str):
            captured_prompt["value"] = prompt
            return "done"

        with (
            patch("gateway.services.merger.detect_language", return_value="english"),
            patch("gateway.services.merger.MERGE_PROMPT", FAKE_MERGE_PROMPT),
            patch.object(merger, "_call_llm", new=capture),
        ):
            await merger.merge(items)

        prompt = captured_prompt["value"]
        assert "--- Alpha ---" in prompt
        assert "alpha content" in prompt
        assert "--- Beta ---" in prompt
        assert "beta content" in prompt

    @pytest.mark.anyio
    async def test_prompt_uses_fallback_name_when_metadata_name_is_none(self):
        merger = make_merger()
        items = [make_input_item("content", name=None)]
        captured_prompt = {}

        async def capture(prompt: str):
            captured_prompt["value"] = prompt
            return "result"

        with (
            patch("gateway.services.merger.detect_language", return_value="english"),
            patch("gateway.services.merger.MERGE_PROMPT", FAKE_MERGE_PROMPT),
            patch.object(merger, "_call_llm", new=capture),
        ):
            await merger.merge(items)

        assert "--- Document 1 ---" in captured_prompt["value"]

    @pytest.mark.anyio
    async def test_doc_count_in_prompt_matches_items_length(self):
        merger = make_merger()
        items = [make_input_item(f"content {i}", name=f"Doc {i}") for i in range(4)]
        captured_prompt = {}

        async def capture(prompt: str):
            captured_prompt["value"] = prompt
            return "done"

        with (
            patch("gateway.services.merger.detect_language", return_value="english"),
            patch("gateway.services.merger.MERGE_PROMPT", FAKE_MERGE_PROMPT),
            patch.object(merger, "_call_llm", new=capture),
        ):
            await merger.merge(items)

        assert "Merge 4 docs:" in captured_prompt["value"]

    @pytest.mark.anyio
    async def test_uses_swedish_prompt_when_majority_swedish(self):
        merger = make_merger()
        items = [make_input_item("hej", name="Sv")]
        captured_prompt = {}

        async def capture(prompt: str):
            captured_prompt["value"] = prompt
            return "resultat"

        with (
            patch("gateway.services.merger.detect_language", return_value="swedish"),
            patch("gateway.services.merger.MERGE_PROMPT", FAKE_MERGE_PROMPT),
            patch.object(merger, "_call_llm", new=capture),
        ):
            await merger.merge(items)

        assert captured_prompt["value"].startswith("Slå ihop")

    @pytest.mark.anyio
    async def test_documents_are_separated_by_double_newline(self):
        merger = make_merger()
        items = [make_input_item("aaa", name="A"), make_input_item("bbb", name="B")]
        captured_prompt = {}

        async def capture(prompt: str):
            captured_prompt["value"] = prompt
            return "done"

        with (
            patch("gateway.services.merger.detect_language", return_value="english"),
            patch("gateway.services.merger.MERGE_PROMPT", FAKE_MERGE_PROMPT),
            patch.object(merger, "_call_llm", new=capture),
        ):
            await merger.merge(items)

        combined_section = captured_prompt["value"].split(":\n", 1)[1]
        assert "\n\n" in combined_section

    @pytest.mark.anyio
    async def test_single_item_does_not_raise(self):
        merger = make_merger()
        items = [make_input_item("solo doc", name="Solo")]

        with (
            patch("gateway.services.merger.detect_language", return_value="english"),
            patch("gateway.services.merger.MERGE_PROMPT", FAKE_MERGE_PROMPT),
            patch.object(merger, "_call_llm", new=AsyncMock(return_value="result")),
        ):
            result = await merger.merge(items)

        assert result is not None
        assert result.summary == "result"
