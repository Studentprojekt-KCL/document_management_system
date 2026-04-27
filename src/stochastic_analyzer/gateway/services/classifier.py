"""Zero-shot NLI classification via external TEI container."""

import asyncio
from json.decoder import JSONDecodeError

import httpx

from gateway.schemas import InputItem, ClassificationResult

from shared_functions.dmis_logger import dms_warning

LABELS = ["Public", "Internal", "Sensitive", "Confidential"]

# These label triggers have been tweaked for hours, only touch if absolutly certain
LABEL_TRIGGERS = [
    "public open-source documentation",
    "internal employee policy or guidelines",
    "sensitive financial review or performance data",
    "confidential strategic project plan",
]


class Classifier:
    """Zero-shot NLI document classifier using an external TEI container.

    Attributes:
        url: URL for the TEI classifier endpoint.
        client: Shared async HTTP client.
        escalation_threshold: Score gap threshold for security-first escalation.
        max_chars: Maximum characters per document for classification.
        batch_size: Number of NLI pairs per batch request.
        timeout: Request timeout in seconds.
    """

    max_chars: int = 2000
    batch_size: int = 32
    timeout: float = 15.0

    def __init__(self, url: str, escalation_threshold: float, client: httpx.AsyncClient) -> None:
        self.url = url
        self.escalation_threshold = escalation_threshold
        self.client = client

    def _build_inputs(self, items: list[InputItem]) -> list[list[str]]:
        """Build NLI premise-hypothesis pairs for all documents."""
        inputs = []
        for item in items:
            doc_name = item.metadata.name or "Unknown Document"
            author = item.metadata.author or "Unknown Author"
            rich_context = f"Name: {doc_name}. Author: {author}. Content: {item.content[:self.max_chars]}"

            for trigger in LABEL_TRIGGERS:
                inputs.append([rich_context, trigger])

        return inputs

    @staticmethod
    def _escalate(doc_scores: list[float], best_index: int, escalation_threshold: float) -> int:
        """Bump classification up if a higher-ranked label is within threshold."""
        label_rank = {"Public": 0, "Internal": 1, "Sensitive": 2, "Confidential": 3}
        original_score = doc_scores[best_index]
        original_rank = label_rank[LABELS[best_index]]
        for i, score in enumerate(doc_scores):
            if label_rank[LABELS[i]] > original_rank and (original_score - score) < escalation_threshold:
                best_index = i
        return best_index

    def _resolve_labels(self, items: list[InputItem], all_scores: list[float]) -> list[ClassificationResult]:
        """Map entailment scores back to classification labels per document."""
        results = []
        num_labels = len(LABELS)
        for doc_idx, item in enumerate(items):
            offset = doc_idx * num_labels
            doc_scores = all_scores[offset : offset + num_labels]
            best_index = doc_scores.index(max(doc_scores))
            best_index = self._escalate(doc_scores, best_index, self.escalation_threshold)
            results.append(
                ClassificationResult(
                    unique_pointer=item.metadata.unique_pointer or "Unknown Document",
                    **{"security_class": LABELS[best_index]},
                )
            )
        return results

    async def classify(self, items: list[InputItem]) -> list[ClassificationResult]:
        """Classify a batch of documents using parallel NLI inference."""
        inputs = self._build_inputs(items)
        all_scores = [0.0] * len(inputs)

        async def fetch_batch(start_idx: int, batch: list[list[str]]) -> None:
            response = await self.client.post(
                f"{self.url}/predict",
                json={"inputs": batch},
                timeout=self.timeout,
            )
            response.raise_for_status()

            for i, class_prediction in enumerate(response.json()):
                score = next(
                    (x["score"] for x in class_prediction if x["label"] == "entailment"),
                    0.0,
                )
                all_scores[start_idx + i] = score

        try:
            tasks = [fetch_batch(i, inputs[i : i + self.batch_size]) for i in range(0, len(inputs), self.batch_size)]
            await asyncio.gather(*tasks)
        except httpx.HTTPStatusError as err:
            dms_warning(f"Unexpected response from {self.url}, {err}")
            return []
        except JSONDecodeError as err:
            dms_warning(f"Response from {self.url} could not be decoded, {err}")
            return []
        except httpx.TimeoutException as err:
            dms_warning(f"Connection to {self.url} timed out, {err}")
            return []

        return self._resolve_labels(items, all_scores)
