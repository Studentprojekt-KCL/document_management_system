"""Zero-shot NLI classification via external TEI container."""

import asyncio
from json.decoder import JSONDecodeError

import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, ClassificationResult

LABELS = ["Public", "Internal", "Sensitive", "Confidential"]

# These label triggers have been tweaked for hours, only touch if absolutley certain
LABEL_TRIGGERS = [
    "publicly available source code, documentation, or open material",
    "internal company policy and employee guidelines",
    "sensitive personal, employee, or security data",
    "strictly confidential executive leadership strategy",
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
    original_score = doc_scores[best_index]
    original_rank = label_rank[LABELS[best_index]]

    for i, score in enumerate(doc_scores):
        if label_rank[LABELS[i]] > original_rank and (original_score - score) < escalation_threshold:
            best_index = i

    return best_index


def _resolve_labels(
    items: list[InputItem],
    all_scores: list[float],
    escalation_threshold: float,
) -> list[ClassificationResult]:
    """Map entailment scores back to classification labels per document."""
    results = []
    num_labels = len(LABELS)
    for doc_idx, item in enumerate(items):
        offset = doc_idx * num_labels
        doc_scores = all_scores[offset : offset + num_labels]
        best_index = doc_scores.index(max(doc_scores))
        if escalation_threshold is not None:
            best_index = _escalate(doc_scores, best_index, escalation_threshold)
        results.append(
            ClassificationResult(
                unique_pointer=item.metadata.unique_pointer or "Unknown Document",
                **{"security_class": LABELS[best_index]},
            )
        )
    return results


async def classify_documents(
    items: list[InputItem], classifier_url: str, escalation_threshold: float
) -> list[ClassificationResult]:
    """Classify a batch of documents using parallel NLI inference against a TEI container."""
    inputs = _build_inputs(items, max_chars=2000)
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
