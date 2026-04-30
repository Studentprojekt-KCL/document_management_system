"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from json import JSONDecodeError
import logging

import httpx

from shared_functions.initialisation_tools import read_env_variable, read_float_env_variable
from shared_functions.dmis_logger import dms_warning


class Classifier:
    """Class handling query connections."""

    CLASSIFY_ENDPOINT: str = "/predict"

    MAX_CHARS: int = 2000
    BATCH_SIZE: int = 4
    TIMEOUT: float = 15.0

    LABELS = ["Public", "Internal", "Sensitive", "Confidential"]
    LABEL_TRIGGERS = [
        "public open-source documentation",
        "internal employee policy or guidelines",
        "sensitive financial review or performance data",
        "confidential strategic project plan",
    ]

    client: httpx.AsyncClient
    escalation_threshold: float
    classifications: list[str]

    def __init__(self) -> None:
        """Constructor."""
        logging.getLogger("httpx").setLevel(logging.WARNING)
        address: str = read_env_variable("SEARCHENG_CLASSIFIER_URL", required=True).rstrip("/") # type: ignore[attr-defined]
        self.client = httpx.AsyncClient(base_url=address)
        self.escalation_threshold = read_float_env_variable("SEARCHENG_CLASSIFIER_ESCALATION_THRESHOLD")

    def _build_inputs(self, items: list[dict]) -> list[list[str]]:
        """Build NLI premise-hypothesis pairs for all documents."""
        inputs = []
        for item in items:
            doc_name = item.get("name", "Unknown Document")
            content = item.get("content", "")[:self.MAX_CHARS]
            rich_context = f"Name: {doc_name}. Content: {content}"

            for trigger in self.LABEL_TRIGGERS:
                inputs.append([rich_context, trigger])

        return inputs

    def _escalate(self, doc_scores: list[float], best_index: int, escalation_threshold: float) -> int:
        """Bump classification up if a higher-ranked label is within threshold."""
        label_rank = {"Public": 0, "Internal": 1, "Sensitive": 2, "Confidential": 3}
        original_score = doc_scores[best_index]
        original_rank = label_rank[self.LABELS[best_index]]
        for i, score in enumerate(doc_scores):
            if label_rank[self.LABELS[i]] > original_rank and (original_score - score) < escalation_threshold:
                best_index = i
        return best_index

    def _resolve_labels(self, items: list[dict], all_scores: list[float]) -> None:
        """Map entailment scores back to classification labels per document."""
        num_labels = len(self.LABELS)
        for doc_idx, item in enumerate(items):
            offset = doc_idx * num_labels
            doc_scores = all_scores[offset : offset + num_labels]
            best_index = doc_scores.index(max(doc_scores))
            best_index = self._escalate(doc_scores, best_index, self.escalation_threshold)
            item.update({"classification": self.LABELS[best_index]})

    async def classify(self, batch: list[dict]) -> None:
        """Classify a batch of documents using parallel NLI inference."""
        inputs = self._build_inputs(batch)
        all_scores = [0.0] * len(inputs)
        try:
            response = await self.client.post(
                self.CLASSIFY_ENDPOINT,
                json={"inputs": inputs},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()

            for i, class_prediction in enumerate(response.json()):
                score = next(
                    (x["score"] for x in class_prediction if x["label"] == "entailment"),
                    0.0,
                )
                all_scores[i] = score
            self._resolve_labels(batch, all_scores)
        except httpx.HTTPStatusError as err:
            dms_warning(f"Unexpected response from classifier, {err}")
        except httpx.ReadError as err:
            dms_warning(f"Could not read response, {err}")
        except JSONDecodeError as err:
            dms_warning(f"Response from classifier could not be decoded, {err}")
        except httpx.TimeoutException as err:
            dms_warning(f"Connection to classifier timed out, {err}")

