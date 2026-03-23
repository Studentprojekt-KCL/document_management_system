"""Batch document summarization via external Ministral LLM."""

from json.decoder import JSONDecodeError

import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, SummaryResult
from gateway.preprompts import SUMMARIZER_PROMPT


async def summarize_documents(items: list[InputItem], ministral_url: str, ministral_model: str) -> SummaryResult | None:
    """Synthesize multiple documents into a single summary via the Ministral LLM."""
    combined_context = ""
    for i, item in enumerate(items, 1):
        doc_name = item.metadata.name or f"Document {i}"
        combined_context += f"\n--- {doc_name} ---\n{item.content}\n"

    prompt = SUMMARIZER_PROMPT.format(combined_context=combined_context)

    payload = {
        "model": ministral_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(ministral_url, json=payload, timeout=120)
            response.raise_for_status()
            summary_text = response.json().get("response", "").strip()
            return SummaryResult(summary=summary_text)
    except httpx.HTTPStatusError as err:
        dms_warning(f"Unexpected response (status code {response.status_code}) from {ministral_url}, {err}")
    except JSONDecodeError as err:
        dms_warning(f"Response from {ministral_url} could not be decoded, {err}")
    except httpx.TimeoutException as err:
        dms_warning(f"Connection to {ministral_url} timed out, {err}")
    return None
