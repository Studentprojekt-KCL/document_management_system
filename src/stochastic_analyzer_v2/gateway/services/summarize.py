"""Summarize logic."""

import asyncio
import aiohttp

from gateway.model_instructions import SUMMARIZER_SYSTEM_PROMPT, SUMMARIZE_PROMPT, MERGE_STAGE_ONE_PROMPT, MERGE_STAGE_TWO_PROMPT
from gateway.schemas import InputItem, SummaryResult

from shared_functions.dmis_logger import dms_warning
from shared_functions.initialisation_tools import read_env_variable


class Summarizer:
    """yeah buddy summarize engine"""

    TIMEOUT: int = 120

    def __init__(self) -> None:
        self.url = read_env_variable("STOCHAN_LLM_URL").rstrip("/")
        self.model = read_env_variable("STOCHAN_LLM_MODEL")
        self.session: aiohttp.ClientSession

    async def init(self) -> None:
        """Open connection."""
        self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close the connection."""
        await self.session.close()

    async def summarize(self, item: InputItem) -> SummaryResult | None:
        """Summarize a single document"""
        prompt = SUMMARIZE_PROMPT.format(content=item.content)
        result = await self._call_llm(prompt)
        if result is None:
            dms_warning("No response recieved")
            return None
        return SummaryResult(summary=result)

    async def merge(self, items: list[InputItem]) -> SummaryResult | None:
        """Handle merging multiple documents into one amazing new document."""
        tasks = [self._call_llm(MERGE_STAGE_ONE_PROMPT.format(content=item.content)) for item in items]
        extracts = [e for e in await asyncio.gather(*tasks) if e is not None]

        if not extracts:
            dms_warning("Extracts in stage 1 failed.")
            return None
        if len(extracts) == 1:
            return SummaryResult(summary=extracts[0])

        combined = "\n\n".join(extracts)
        prompt = MERGE_STAGE_TWO_PROMPT.format(doc_count=len(extracts), combined_summaries=combined)
        result = await self._call_llm(prompt)
        return SummaryResult(summary=result) if result else None

    async def _call_llm(self, prompt: str) -> str | None:
        """Send the prompt to an LLM and return response text."""
        try:
            async with self.session.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": SUMMARIZER_SYSTEM_PROMPT,
                    "stream": False,
                },
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            dms_warning(f"LLM request failed: {err}")
            return None

        if not isinstance(data, dict):
            dms_warning(f"Unexpected LLM response shape: {type(data).__name__}")
            return None
        return data.get("response", "").strip() or None
