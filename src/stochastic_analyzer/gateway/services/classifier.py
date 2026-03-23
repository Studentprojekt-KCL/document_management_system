"""Zero-shot NLI classification via external TEI container."""

import asyncio
from json.decoder import JSONDecodeError
import httpx
from gateway.schemas import InputItem, ClassificationResult
from dmis_logger import dms_warning


async def classify_documents(items: list[InputItem], classifier_url: str) -> list[ClassificationResult]:
    """Classify a batch of documents using parallel NLI inference against a TEI container."""
    labels = ["Public", "Internal", "Sensitive", "Confidential"]
    batch_size = 32
    max_chars = 800

    label_triggers = {
        "Public": "This information is common knowledge and intended for the general public.",
        "Internal": "This is standard corporate communication for regular employees.",
        "Sensitive": "This document contains restricted technical or operational data like passwords or keys.",
        "Confidential": "This is a strictly secret document containing high-level CEO strategy, mergers, or financial projections.",
    }

    inputs = []
    for item in items:
        doc_name = item.metadata.name or "Unknown Document"
        author = item.metadata.author or "Unknown Author"
        rich_context = f"Name: {doc_name}. Author: {author}. Content: {item.content[:max_chars]}"

        for _, trigger in label_triggers.items():
            inputs.append([rich_context, trigger])

    all_scores = [0.0] * len(inputs)

    async def fetch_batch(client: httpx.AsyncClient, start_idx: int, batch: list[list[str]]):
        response = await client.post(
            f"{classifier_url}/predict",
            json={"inputs": batch},
            timeout=15.0,
        )
        response.raise_for_status()
        predictions = response.json()

        for i, class_prediction in enumerate(predictions):
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

    results = []
    num_labels = len(labels)
    for doc_idx, item in enumerate(items):
        offset = doc_idx * num_labels
        doc_scores = all_scores[offset : offset + num_labels]
        best_index = doc_scores.index(max(doc_scores))
        final_label = labels[best_index]

        results.append(
            ClassificationResult(
                name=item.metadata.name or "Unknown Document",
                **{"Security-class": final_label},
            )
        )

    return results
