"""Batch document summarization via external Ministral LLM."""

import asyncio
from json.decoder import JSONDecodeError

import httpx

from dmis_logger import dms_warning
from gateway.preprompts import INDIVIDUAL_SUMMARY_PROMPT, SYNTHESIS_PROMPT
from gateway.schemas import InputItem, SummaryResult
from gateway.preprompts import SUMMARIZER_PROMPT, SUMMARIZER_SYSTEM_PROMPT, HEADERS
from gateway.config import ServiceConfig, LanguageConfig

# Language detection constants
SWEDISH_CHARS = set("åäöÅÄÖ")
SWEDISH_STOPWORDS = {"och", "är", "det", "på", "i", "av", "för", "med", "som", "att", "en", "ett", "den", "der"}

def detect_language(text: str, config: LanguageConfig) -> str:
    """Detect Swedish via early-exit heuristic on sampled prefix. Fast & injection-resistant."""
    if len(text) < config.min_doc_length:
        return "english"

    # Sample only the beginning (where language signals usually appear)
    sample = text[: config.sample_size].lower()
    # Early-exit character check
    swedish_char_count = 0
    for char in sample:
        if char in SWEDISH_CHARS:
            swedish_char_count += 1
            if swedish_char_count >= config.swedish_char_threshold:
                return "swedish"

    # Fallback: check for common Swedish stopwords (≥3 matches = likely Swedish)
    words = sample.split()
    swedish_word_hits = sum(1 for word in words if word in SWEDISH_STOPWORDS)
    return "swedish" if swedish_word_hits >= config.swedish_stopword_threshold else "english"


async def summarize_documents(
    items: list[InputItem],
    service_config: ServiceConfig,
) -> SummaryResult | None:
    """Synthesize multiple documents into a single summary via the Ministral LLM."""
    combined_context = ""
    for i, item in enumerate(items, 1):
        doc_name = item.metadata.name or f"Document {i}"
        combined_context += f"\n--- {doc_name} ---\n{item.content}\n"

    language = detect_language(combined_context, service_config.language)
    headers = HEADERS[language]

    prompt = SUMMARIZER_PROMPT.format(
        combined_context=combined_context,
        language=language,
        highlights_header=headers["highlights"],
        summary_header=headers["summary"],
    )

    payload = {
        "model": service_config.ministral.model,
        "system": SUMMARIZER_SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "max_tokens": service_config.ministral.max_tokens,
        "temperature": service_config.ministral.temperature,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                service_config.ministral.url,
                json=payload,
                timeout=service_config.ministral.timeout,
            )
            response.raise_for_status()
            summary_text = response.json().get("response", "").strip()
            return SummaryResult(summary=summary_text)
    except httpx.HTTPStatusError as err:
        dms_warning(f"Unexpected response (status code {response.status_code}) from {service_config.ministral.url}, {err}")
    except JSONDecodeError as err:
        dms_warning(f"Response from {service_config.ministral.url} could not be decoded, {err}")
    except httpx.TimeoutException as err:
        dms_warning(f"Connection to {service_config.ministral.url} timed out, {err}")
    return None


async def _synthesize(
    per_doc_blocks: list[str],
    ministral_url: str,
    ministral_model: str,
    timeout: int = 120,
) -> SummaryResult | None:
    """Synthesize individual summaries into a final combined summary."""
    combined_summaries = "\n\n".join(per_doc_blocks)
    prompt = SYNTHESIS_PROMPT.format(
        doc_count=len(per_doc_blocks),
        combined_summaries=combined_summaries,
    )

    async with httpx.AsyncClient() as client:
        result = await _call_llm(client, prompt, ministral_url, ministral_model, timeout)

    if result is None:
        return None
    return SummaryResult(summary=result)


async def summarize_documents(
    items: list[InputItem],
    ministral_url: str,
    ministral_model: str,
    timeout: int = 120,
) -> SummaryResult | None:
    """Synthesize multiple documents into a single summary via a two-stage approach."""

    # --- Stage 1: Summarize each document individually (in parallel) ---
    async with httpx.AsyncClient() as client:
        tasks = []
        doc_names = []
        for i, item in enumerate(items, 1):
            name = item.metadata.name or f"Document {i}"
            doc_names.append(name)
            prompt = INDIVIDUAL_SUMMARY_PROMPT.format(doc_name=name, content=item.content)
            tasks.append(_call_llm(client, prompt, ministral_url, ministral_model, timeout))

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

    # --- Stage 2: Synthesize individual summaries into a final output ---
    return await _synthesize(per_doc_blocks, ministral_url, ministral_model, timeout)
