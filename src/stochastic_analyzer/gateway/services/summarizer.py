"""Batch document summarization via external Ministral LLM."""

from json.decoder import JSONDecodeError

import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, SummaryResult
from gateway.preprompts import INDIVIDUAL_SUMMARY_PROMPT, SYNTHESIS_PROMPT
import asyncio


async def _summarize_single(
    doc_name: str,
    content: str,
    client: httpx.AsyncClient,
    ministral_url: str,
    ministral_model: str,
) -> str | None:
    """Summarize a single document."""
    prompt = INDIVIDUAL_SUMMARY_PROMPT.format(doc_name=doc_name, content=content)
    payload = {"model": ministral_model, "prompt": prompt, "stream": False}
 
    try:
        response = await client.post(ministral_url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except httpx.HTTPStatusError as err:
        dms_warning(f"Unexpected response (status code {response.status_code}) from {ministral_url}, {err}")
    except JSONDecodeError as err:
        dms_warning(f"Response from {ministral_url} could not be decoded, {err}")
    except httpx.TimeoutException as err:
        dms_warning(f"Connection to {ministral_url} timed out, {err}")
    return None
 
 
async def summarize_documents(
    items: list[InputItem], ministral_url: str, ministral_model: str
) -> SummaryResult | None:
    """Synthesize multiple documents into a single summary via a two-stage approach."""
 
    # --- Stage 1: Summarize each document individually (in parallel) ---
    async with httpx.AsyncClient() as client:
        tasks = []
        doc_names = []
        for i, item in enumerate(items, 1):
            name = item.metadata.name or f"Document {i}"
            doc_names.append(name)
            tasks.append(
                _summarize_single(name, item.content, client, ministral_url, ministral_model)
            )
 
        individual_summaries = await asyncio.gather(*tasks)
 
    # Build context from successful summaries only
    per_doc_blocks = []
    for name, summary in zip(doc_names, individual_summaries):
        if summary:
            per_doc_blocks.append(f"--- {name} ---\n{summary}")
 
    if not per_doc_blocks:
        return None
    
    if len(per_doc_blocks) == 1:
        return SummaryResult(summary=individual_summaries[0])
 
    # --- Stage 2: Synthesize individual summaries into a final output ---
    combined_summaries = "\n\n".join(per_doc_blocks)
    prompt = SYNTHESIS_PROMPT.format(
        doc_count=len(per_doc_blocks),
        combined_summaries=combined_summaries,
    )
    payload = {"model": ministral_model, "prompt": prompt, "stream": False}
 
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