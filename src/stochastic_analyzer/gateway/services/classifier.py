"""Zero-shot NLI classification via external TEI container."""

import asyncio
from json.decoder import JSONDecodeError

import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, ClassificationResult

LABELS = ["Public", "Internal", "Sensitive", "Confidential"]

LABEL_TRIGGERS = [
    "This information is common knowledge and intended for the general public.",
    "This is standard corporate communication for regular employees.",
    "This document contains restricted technical or operational data like passwords or keys.",
    "This is a strictly secret document containing high-level CEO strategy, mergers, or financial projections.",
]


def _build_inputs(items: list[InputItem], max_chars: int) -> list[list[str]]:
    """Build NLI premise-hypothesis pairs for all documents."""
    inputs = []
    for item in items:
        doc_name = item.metadata.name or "Unknown Document"
        author = item.metadata.author or "Unknown Author"
        rich_context = f"Name: {doc_name}. Author: {author}. Content: {item.content[:max_chars]}"

        for trigger in LABEL_TRIGGERS:
            inputs.append([rich_context, trigger])

    return inputs


def _resolve_labels(items: list[InputItem], all_scores: list[float]) -> list[ClassificationResult]:
    """Map entailment scores back to classification labels per document."""
    results = []
    num_labels = len(LABELS)

    for doc_idx, item in enumerate(items):
        offset = doc_idx * num_labels
        doc_scores = all_scores[offset : offset + num_labels]
        best_index = doc_scores.index(max(doc_scores))

        results.append(
            ClassificationResult(
                name=item.metadata.name or "Unknown Document",
                **{"Security-class": LABELS[best_index]},
            )
        )

    return results


async def classify_documents(items: list[InputItem], classifier_url: str) -> list[ClassificationResult]:
    """Classify a batch of documents using parallel NLI inference against a TEI container."""
    inputs = _build_inputs(items, max_chars=800)
    all_scores = [0.0] * len(inputs)
    batch_size = 32

    async def fetch_batch(client: httpx.AsyncClient, start_idx: int, batch: list[list[str]]) -> None:
        response = await client.post(
            f"{classifier_url}/predict",
            json={"inputs": batch},
            timeout=15.0,
        )
        response.raise_for_status()

        for i, class_prediction in enumerate(response.json()):
            score = next((x["score"] for x in class_prediction if x["label"] == "entailment"), 0.0)
            all_scores[start_idx + i] = score

    try:
        async with httpx.AsyncClient() as client:
            tasks = [fetch_batch(client, i, inputs[i : i + batch_size]) for i in range(0, len(inputs), batch_size)]
            await asyncio.gather(*tasks)
    except httpx.HTTPStatusError as err:
        dms_warning(f"Unexpected response from {classifier_url}, {err}")
        return []
    except JSONDecodeError as err:
        dms_warning(f"Response from {classifier_url} could not be decoded, {err}")
        return []
    except httpx.TimeoutException as err:
        dms_warning(f"Connection to {classifier_url} timed out, {err}")
        return []

    return _resolve_labels(items, all_scores)
