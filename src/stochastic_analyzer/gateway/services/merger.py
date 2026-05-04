"""Document merger via external Ministral LLM."""

from dataclasses import dataclass
from json.decoder import JSONDecodeError

import httpx

from gateway.preprompts import MERGE_PROMPT, MERGER_SYSTEM_PROMPT
from gateway.schemas import InputItem, SummaryResult
from gateway.services.summarizer import LanguageConfig, detect_language

from shared_functions.dmis_logger import dms_warning
from shared_functions.initialisation_tools import read_env_variable, read_int_env_variable


@dataclass
class MergerConfig:
    """Configuration for the Merger service."""

    url: str
    model: str
    timeout: int
    lang_config: LanguageConfig


class Merger:
    """Fuses multiple similar documents into one coherent document via an external LLM.

    Attributes:
        url: URL for the LLM endpoint.
        model: Model identifier.
        client: Shared async HTTP client.
        timeout: Request timeout in seconds.
        lang_config: Configuration for language detection.
    """

    def __init__(self, config: MergerConfig, client: httpx.AsyncClient) -> None:
        self.url = config.url
        self.model = config.model
        self.timeout = config.timeout
        self.lang_config = config.lang_config
        self.client = client

    @classmethod
    def from_env(cls, client: httpx.AsyncClient) -> "Merger":
        """Construct a Merger from environment variables."""
        config = MergerConfig(
            url=read_env_variable("STOCHAN_LLM_URL"),
            model=read_env_variable("STOCHAN_LLM_MODEL"),
            timeout=read_int_env_variable("STOCHAN_LLM_TIMEOUT"),
            lang_config=LanguageConfig(
                sample_size=read_int_env_variable("STOCHAN_SAMPLE_SIZE"),
                swedish_char_threshold=read_int_env_variable("STOCHAN_SWEDISH_CHAR_THRESHOLD"),
            ),
        )
        return cls(config=config, client=client)

    async def _call_llm(self, prompt: str) -> str | None:
        """Send a prompt to the LLM and return the response text."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": MERGER_SYSTEM_PROMPT,
            "stream": False,
        }
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

    async def merge(self, items: list[InputItem]) -> SummaryResult | None:
        """Fuse multiple similar documents into one coherent document."""
        language = self._detect_majority_language(items)

        blocks = []
        for i, item in enumerate(items, 1):
            name = item.metadata.name or f"Document {i}"
            blocks.append(f"--- {name} ---\n{item.content}")

        combined = "\n\n".join(blocks)
        prompt = MERGE_PROMPT[language].format(
            doc_count=len(items),
            combined_documents=combined,
        )
        result = await self._call_llm(prompt)

        if result is None:
            return None
        return SummaryResult(summary=result)
