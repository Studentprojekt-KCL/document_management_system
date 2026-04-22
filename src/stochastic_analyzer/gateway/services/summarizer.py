"""Batch document summarization via external Ministral LLM."""

import asyncio
from json.decoder import JSONDecodeError

import httpx

from gateway.config import LanguageConfig
from gateway.preprompts import (
    INDIVIDUAL_SUMMARY_PROMPT,
    SYNTHESIS_PROMPT,
    SUMMARIZER_SYSTEM_PROMPT,
)
from gateway.schemas import InputItem, SummaryResult
from shared_functions.dmis_logger import dms_warning

SWEDISH_CHARS = set("åäö")


def detect_language(text: str, sample_size: int, swedish_char_threshold: int) -> str:
    """Detect Swedish via early-exit heuristic on sampled prefix. Fast & injection-resistant."""

    sample = text[:sample_size].lower()

    swedish_char_count = 0
    for char in sample:
        if char in SWEDISH_CHARS:
            swedish_char_count += 1
            if swedish_char_count >= swedish_char_threshold:
                return "swedish"

    return "english"


class Summarizer:
    """Two-stage document summarizer using an external LLM.

    Attributes:
        url: URL for the LLM endpoint.
        model: Model identifier.
        timeout: Request timeout in seconds.
        lang_config: Configuration for language detection.
    """

    def __init__(
        self,
        url: str,
        model: str,
        timeout: int,
        lang_config: LanguageConfig,
    ) -> None:
        self.url = url
        self.model = model
        self.timeout = timeout
        self.lang_config = lang_config

    async def _call_llm(self, client: httpx.AsyncClient, prompt: str) -> str | None:
        """Send a prompt to the LLM and return the response text."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": SUMMARIZER_SYSTEM_PROMPT,
            "stream": False,
        }
        try:
            response = await client.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except httpx.HTTPStatusError as err:
            dms_warning(f"Unexpected response (status code {response.status_code}) from {self.url}, {err}")
        except JSONDecodeError as err:
            dms_warning(f"Response from {self.url} could not be decoded, {err}")
        except httpx.TimeoutException as err:
            dms_warning(f"Connection to {self.url} timed out, {err}")
        return None

    def _detect_majority_language(self, items: list[InputItem]) -> str:
        """Detect the majority language across all documents."""
        swedish_count = sum(
            detect_language(
                item.content,
                self.lang_config.sample_size,
                self.lang_config.swedish_char_threshold,
            )
            == "swedish"
            for item in items
        )
        return "swedish" if swedish_count > len(items) / 2 else "english"

    async def summarize(self, items: list[InputItem]) -> SummaryResult | None:
        """Synthesize multiple documents into a single summary via a two-stage approach."""

        language = self._detect_majority_language(items)

        async with httpx.AsyncClient() as client:
            # Stage 1: Summarize each document individually (in parallel)
            tasks = []
            doc_names = []
            for i, item in enumerate(items, 1):
                name = item.metadata.name or f"Document {i}"
                doc_names.append(name)
                prompt = INDIVIDUAL_SUMMARY_PROMPT[language].format(
                    doc_name=name,
                    content=item.content,
                )
                tasks.append(self._call_llm(client, prompt))
            individual_summaries = await asyncio.gather(*tasks)

            # Build context from successful summaries only
            per_doc_blocks = []
            for name, summary in zip(doc_names, individual_summaries, strict=True):
                if summary:
                    per_doc_blocks.append(f"--- {name} ---\n{summary}")

            if not per_doc_blocks:
                return None

            # Short-circuit: skip synthesis for a single document
            if len(per_doc_blocks) == 1:
                return SummaryResult(summary=individual_summaries[0])

            # Stage 2: Synthesize individual summaries into a final output
            combined = "\n\n".join(per_doc_blocks)
            prompt = SYNTHESIS_PROMPT[language].format(
                doc_count=len(per_doc_blocks),
                combined_summaries=combined,
            )
            result = await self._call_llm(client, prompt)

        if result is None:
            return None
        return SummaryResult(summary=result)
