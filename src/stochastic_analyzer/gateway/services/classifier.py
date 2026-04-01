"""Zero-shot NLI classification via external TEI container."""

import asyncio
from json.decoder import JSONDecodeError

import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, ClassificationResult

LABELS = ["Public", "Internal", "Sensitive", "Confidential"]

LABEL_TRIGGERS = [
    # Public
    "This is general information intended for the public, such as manuals, public announcements, or open event invitations.",
    # Internal
    "This is internal company information meant only for employees, such as sales targets, project plans, "
    "team updates, system migrations, or internal process changes.",
    # Sensitive
    "This document contains sensitive employee or operational data such as performance reviews, "
    "salary information, disciplinary records, access credentials, or HR matters.",
    # Confidential
    "This is strictly confidential information such as executive strategy, mergers and acquisitions, "
    "financial projections, medical records, patient data, or personal identification numbers.",
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


def _escalate(doc_scores: list[float], best_index: int, escalation_threshold: float) -> int:
    """Bump classification up if a higher-ranked label is within threshold."""
    label_rank = {"Public": 0, "Internal": 1, "Sensitive": 2, "Confidential": 3}
    best_score = doc_scores[best_index]

    for i, score in enumerate(doc_scores):
        is_higher_rank = label_rank[LABELS[i]] > label_rank[LABELS[best_index]]
        is_within_threshold = (best_score - score) < escalation_threshold

        if is_higher_rank and is_within_threshold:
            best_index = i
            best_score = score

    return best_index


def _resolve_labels(items: list[InputItem], all_scores: list[float], escalation_threshold: float) -> list[ClassificationResult]:
    """Map entailment scores back to classification labels per document."""
    results = []
    num_labels = len(LABELS)

    for doc_idx, item in enumerate(items):
        # Slice out the document's 4 scores from the flat list
        offset = doc_idx * num_labels
        doc_scores = all_scores[offset : offset + num_labels]

        # Start with the highest score label as our best guess
        best_index = doc_scores.index(max(doc_scores))

        # Chained escalation: bump up if a higher-ranked label is close enough
        best_index = _escalate(doc_scores, best_index, escalation_threshold)

        results.append(
            ClassificationResult(
                name=item.metadata.name or "Unknown Document",
                **{"Security-class": LABELS[best_index]},
            )
        )

    return results


async def classify_documents(
    items: list[InputItem], classifier_url: str, escalation_threshold: float
) -> list[ClassificationResult]:
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

    return _resolve_labels(items, all_scores, escalation_threshold)
