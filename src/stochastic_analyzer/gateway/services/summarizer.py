"""Batch document summarization via external Ministral LLM."""

from json.decoder import JSONDecodeError

import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, SummaryResult
from gateway.preprompts import SUMMARIZER_PROMPT, SUMMARIZER_SYSTEM_PROMPT, HEADERS

# Language detection constants
SWEDISH_CHARS = set("åäöÅÄÖ")
SWEDISH_STOPWORDS = {"och", "är", "det", "på", "i", "av", "för", "med", "som", "att", "en", "ett", "den", "der"}
MIN_DOC_LENGTH = 50
SAMPLE_SIZE = 5000  # Only scan first 5K chars for language detection

def detect_language(text: str) -> str:
    """Detect Swedish via early-exit heuristic on sampled prefix. Fast & injection-resistant."""
    if len(text) < MIN_DOC_LENGTH:
        return "english"

    # Sample only the beginning (where language signals usually appear)
    sample = text[:SAMPLE_SIZE].lower()

    # Early-exit character check
    swedish_char_count = 0
    for char in sample:
        if char in SWEDISH_CHARS:
            swedish_char_count += 1
            if swedish_char_count >= 2:
                return "swedish"

    # Fallback: check for common Swedish stopwords (≥3 matches = likely Swedish)
    words = sample.split()
    swedish_word_hits = sum(1 for word in words if word in SWEDISH_STOPWORDS)
    return "swedish" if swedish_word_hits >= 3 else "english"

async def summarize_documents(items: list[InputItem], ministral_url: str, ministral_model: str) -> SummaryResult | None:
    """Synthesize multiple documents into a single summary via the Ministral LLM."""
    combined_context = ""
    for i, item in enumerate(items, 1):
        doc_name = item.metadata.name or f"Document {i}"
        combined_context += f"\n--- {doc_name} ---\n{item.content}\n"

    language = detect_language(combined_context)
    headers = HEADERS[language]

    prompt = SUMMARIZER_PROMPT.format(
        combined_context=combined_context,
        language=language,
        highlights_header=headers["highlights"],
        summary_header=headers["summary"],
    )

    payload = {
        "model": ministral_model,
        "system": SUMMARIZER_SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "max_tokens": 400,  # 150 for summary + 250 for bullets
        "temperature": 0.3,
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
