"""Batch document summarization via external Ministral LLM."""

import asyncio
from json.decoder import JSONDecodeError

import httpx

from gateway.preprompts import INDIVIDUAL_SUMMARY_PROMPT, SYNTHESIS_PROMPT
from gateway.schemas import InputItem, SummaryResult

from shared_functions.dmis_logger import dms_error, dms_warning
from shared_functions.initialisation_tools import read_env_variable


class Summarizer:
    """Two-stage document summarizer using an external LLM.

    Attributes:
        url: URL for the LLM endpoint.
        model: Model identifier.
        client: Shared async HTTP client.
        timeout: Request timeout in seconds.
    """

    def __init__(self, url: str, model: str, client: httpx.AsyncClient, timeout: int = 120) -> None:
        self.url = url
        self.model = model
        self.client = client
        self.timeout = timeout

    @classmethod
    def from_env(cls, client: httpx.AsyncClient) -> "Summarizer":
        """Construct a Summarizer from environment variables.

        Reads:
            STOCHAN_LLM_URL: URL for the LLM endpoint.
            STOCHAN_LLM_MODEL: Model identifier.
            STOCHAN_LLM_TIMEOUT: Request timeout in seconds.

        Raises:
            RuntimeError: If any required variable is missing.
        """
        url = read_env_variable("STOCHAN_LLM_URL")
        model = read_env_variable("STOCHAN_LLM_MODEL")
        timeout = read_env_variable("STOCHAN_LLM_TIMEOUT")

        missing = [
            name
            for name, value in (
                ("STOCHAN_LLM_URL", url),
                ("STOCHAN_LLM_MODEL", model),
                ("STOCHAN_LLM_TIMEOUT", timeout),
            )
            if value is None
        ]
        if missing:
            dms_error(f"Summarizer env vars not defined: {', '.join(missing)}")
            raise RuntimeError(f"Missing env vars: {missing}")

        return cls(url=url, model=model, client=client, timeout=int(timeout))

    async def _call_llm(self, prompt: str) -> str | None:
        """Send a prompt to the LLM and return the response text."""
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        try:
            response = await self.client.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except httpx.HTTPStatusError as err:
            dms_warning(f"Unexpected response (status code {err.response.status_code}) from {self.url}, {err}")
        except JSONDecodeError as err:
            dms_warning(f"Response from {self.url} could not be decoded, {err}")
        except httpx.TimeoutException as err:
            dms_warning(f"Connection to {self.url} timed out, {err}")
        return None

    async def summarize(self, items: list[InputItem]) -> SummaryResult | None:
        """Synthesize multiple documents into a single summary via a two-stage approach."""
        # Stage 1: Summarize each document individually (in parallel)
        tasks = []
        doc_names = []
        for i, item in enumerate(items, 1):
            name = item.metadata.name or f"Document {i}"
            doc_names.append(name)
            prompt = INDIVIDUAL_SUMMARY_PROMPT.format(doc_name=name, content=item.content)
            tasks.append(self._call_llm(prompt))

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
        prompt = SYNTHESIS_PROMPT.format(
            doc_count=len(per_doc_blocks),
            combined_summaries=combined,
        )
        result = await self._call_llm(prompt)

        if result is None:
            return None
        return SummaryResult(summary=result)
