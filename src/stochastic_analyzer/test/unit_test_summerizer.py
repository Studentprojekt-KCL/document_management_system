"""Unit tests for Summarizer."""

import unittest
from unittest import IsolatedAsyncioTestCase, mock

from gateway.schemas import InputItem, MetadataTemplate
from gateway.services.summarize import Summarizer


def _make_item(content: str, pointer: str = "p1", name: str | None = None) -> InputItem:
    return InputItem(
        content=content,
        metadata=MetadataTemplate(unique_pointer=pointer, name=name),
    )


def _make_summarizer() -> Summarizer:
    """Build a Summarizer without running its env-reading __init__."""
    with mock.patch.object(Summarizer, "__init__", return_value=None):
        instance = Summarizer()
    instance.url = "http://llm.test"
    instance.model = "test-model"
    return instance


# --------------------------------------------------------------------------- #
# Summarizer.summarize
# --------------------------------------------------------------------------- #
class TestSummarize(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.instance = _make_summarizer()

    async def test_empty_items_returns_empty_summary(self):
        result = await self.instance.summarize([])
        self.assertEqual(result, {"summary": ""})

    async def test_single_document_returns_summary(self):
        with mock.patch.object(self.instance, "_call_llm", new=mock.AsyncMock(return_value="SUMMARY")) as call:
            result = await self.instance.summarize([_make_item("content")])

        self.assertEqual(result, {"summary": "SUMMARY"})
        call.assert_awaited_once()

    async def test_single_document_llm_failure_returns_none(self):
        with mock.patch.object(self.instance, "_call_llm", new=mock.AsyncMock(return_value=None)):
            result = await self.instance.summarize([_make_item("content")])
        self.assertIsNone(result)

    async def test_multiple_documents_runs_two_stages(self):
        items = [_make_item("a"), _make_item("b")]
        # 2 stage-one calls + 1 stage-two call
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(side_effect=["E1", "E2", "FINAL"]),
        ) as call:
            result = await self.instance.summarize(items)

        self.assertEqual(result, {"summary": "FINAL"})
        self.assertEqual(call.await_count, 3)

    async def test_all_stage_one_failures_returns_none(self):
        items = [_make_item("a"), _make_item("b")]
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(return_value=None),
        ):
            result = await self.instance.summarize(items)
        self.assertIsNone(result)

    async def test_partial_stage_one_failure_still_synthesizes(self):
        """One stage-one failure shouldn't block synthesis on the rest."""
        items = [_make_item("a"), _make_item("b"), _make_item("c")]
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(side_effect=[None, "E2", "E3", "FINAL"]),
        ) as call:
            result = await self.instance.summarize(items)

        self.assertEqual(result, {"summary": "FINAL"})
        self.assertEqual(call.await_count, 4)

    async def test_stage_two_failure_returns_none(self):
        items = [_make_item("a"), _make_item("b")]
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(side_effect=["E1", "E2", None]),
        ):
            result = await self.instance.summarize(items)
        self.assertIsNone(result)

    async def test_combined_exceeds_limit_returns_empty_and_skips_stage_two(self):
        items = [_make_item("a"), _make_item("b")]
        oversized = "x" * (Summarizer.MAX_COMBINED_CHARS + 1)
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(side_effect=[oversized, "E2"]),
        ) as call:
            result = await self.instance.summarize(items)

        self.assertEqual(result, {"summary": ""})
        # Only the two stage-one calls happened; stage two was skipped.
        self.assertEqual(call.await_count, 2)


# --------------------------------------------------------------------------- #
# Summarizer.merge
# --------------------------------------------------------------------------- #
class TestMerge(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.instance = _make_summarizer()

    async def test_merge_success_runs_two_stages(self):
        items = [_make_item("a"), _make_item("b")]
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(side_effect=["E1", "E2", "MERGED"]),
        ) as call:
            result = await self.instance.merge(items)

        self.assertEqual(result, {"summary": "MERGED"})
        self.assertEqual(call.await_count, 3)

    async def test_merge_all_stage_one_fail_returns_none(self):
        items = [_make_item("a"), _make_item("b")]
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(return_value=None),
        ):
            self.assertIsNone(await self.instance.merge(items))

    async def test_merge_stage_two_failure_returns_none(self):
        items = [_make_item("a"), _make_item("b")]
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(side_effect=["E1", "E2", None]),
        ):
            self.assertIsNone(await self.instance.merge(items))

    async def test_merge_combined_exceeds_limit_returns_empty(self):
        items = [_make_item("a"), _make_item("b")]
        oversized = "x" * (Summarizer.MAX_COMBINED_CHARS + 1)
        with mock.patch.object(
            self.instance,
            "_call_llm",
            new=mock.AsyncMock(side_effect=[oversized, "E2"]),
        ):
            result = await self.instance.merge(items)
        self.assertEqual(result, {"summary": ""})

    async def test_merge_stage_two_prompt_includes_stage_one_extracts(self):
        """Stage-one outputs should be joined into the stage-two prompt."""
        items = [_make_item("alpha"), _make_item("beta")]
        captured: dict[str, str] = {}

        async def fake_call(prompt: str) -> str:
            if "alpha" in prompt:
                return "EXTRACT-ALPHA"
            if "beta" in prompt:
                return "EXTRACT-BETA"
            captured["stage_two_prompt"] = prompt
            return "MERGED"

        with mock.patch.object(self.instance, "_call_llm", new=fake_call):
            await self.instance.merge(items)

        self.assertIn("EXTRACT-ALPHA", captured["stage_two_prompt"])
        self.assertIn("EXTRACT-BETA", captured["stage_two_prompt"])


if __name__ == "__main__":
    unittest.main()
