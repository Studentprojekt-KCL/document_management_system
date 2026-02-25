"""Ranking logic for embedded model."""

from sentence_transformers import CrossEncoder
import torch
from embedded_ranker.config import settings
from embedded_ranker.schemas import DocumentObject


class RankerService:
    """Class for ranking."""

    def __init__(self) -> None:
        """Start model."""
        print(f"Loading Re-Ranker {settings.MODEL_NAME} ON {settings.DEVICE}")

        self.model = CrossEncoder(
            settings.MODEL_NAME, device=settings.DEVICE, max_length=1024, model_kwargs={"torch_dtype": torch.bfloat16}
        )

    def rank(self, query: str, documents: list[DocumentObject]) -> list[float]:
        """Ranking logic."""

        if not documents:
            return []

        pairs = []
        for doc in documents:
            combined_text = f"{doc.title} {doc.content}"[:1024]
            pairs.append([query, combined_text])

        scores = self.model.predict(pairs, batch_size=256)

        return scores.tolist()
