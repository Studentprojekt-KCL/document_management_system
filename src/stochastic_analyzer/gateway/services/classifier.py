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


def _resolve_labels(items: list[InputItem], all_scores: list[float]) -> list[ClassificationResult]:
    """Map entailment scores back to classification labels per document."""
    escalation_threshold = 0.02
    label_rank = {"Public": 0, "Internal": 1, "Sensitive": 2, "Confidential": 3}

    results = []
    num_labels = len(LABELS)

    for doc_idx, item in enumerate(items):
        # Slice out the document's 4 scores from the flat list
        offset = doc_idx * num_labels
        doc_scores = all_scores[offset : offset + num_labels]

        # Pair each label with its score, sorted highest score first
        scored = sorted(
            [(LABELS[i], doc_scores[i]) for i in range(num_labels)],
            key=lambda x: x[1],
            reverse=True,
        )
        # Start with the highest score label as our best guess
        best_label, best_score = scored[0]

        # Chained escalation: step through ranks, escalating if each gap is within threshold (escalation_threshold)
        for label, score in sorted(scored, key=lambda x: label_rank[x[0]]):

            # Is the next label within the threshold or not?
            if label_rank[label] > label_rank[best_label] and (best_score - score) < escalation_threshold:
                best_label = label
                best_score = score

        results.append(
            ClassificationResult(
                name=item.metadata.name or "Unknown Document",
                **{"Security-class": best_label},
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
