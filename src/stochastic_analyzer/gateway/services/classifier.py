import httpx
from json.decoder import JSONDecodeError
from gateway.config import Settings
from gateway.schemas import InputItem, ClassificationResult
from dmis_logger import dms_warning

async def classify_document(item: InputItem) -> ClassificationResult | None:
    settings = Settings() #Please migrate from this
    labels = ["Public", "Internal", "Sensitive", "Confidential"]

    doc_name = item.metadata.name or "Unknown Document"
    author = item.metadata.author or "Unknown Author"

    rich_context = f"Name: {doc_name}. Author: {author}. Content: {item.content[:1500]}"
    label_triggers = {
    "Public": "This information is common knowledge and intended for the general public.",
    "Internal": "This is standard corporate communication for regular employees.",
    "Sensitive": "This document contains restricted technical or operational data like passwords or keys.",
    "Confidential": "This is a strictly secret document containing high-level CEO strategy, mergers, or financial projections."
    }
    inputs = [
    [rich_context, trigger]
    for _, trigger in label_triggers.items()
    ]

    payload = {"inputs": inputs}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{settings.CLASSIFIER_URL}/predict", json=payload, timeout=30.0)
            response.raise_for_status()
            predictions = response.json()

            entailment_scores = []
            for class_prediction in predictions:
                score = next((x["score"] for x in class_prediction if x["label"] == "entailment"), 0.0)
                entailment_scores.append(score)
            best_index = entailment_scores.index(max(entailment_scores))
            final_label = labels[best_index]

            return ClassificationResult(
                name=doc_name,
                **{"Security-class": final_label}
            )
    except httpx.HTTPStatusError as err:
        dms_warning(f"Unexpected response (status code {response.status_code}) from {settings.MINISTRAL_URL}, {err}")
    except JSONDecodeError as err:
        dms_warning(f"Response from {settings.MINISTRAL_URL} could not be decoded, {err}")
    except httpx.TimeoutException as err:
        dms_warning(f"Connection to {settings.MINISTRAL_URL} timed out, {err}")
    return None
