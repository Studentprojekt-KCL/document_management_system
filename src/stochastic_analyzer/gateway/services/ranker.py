"""Ranking logic for embedded model."""

from sentence_transformers import CrossEncoder
import torch
from gateway.config import Settings
from gateway.schemas import DocumentObject
from dmis_logger import dms_info


class RankerService:
    """Class for ranking."""

    def __init__(self) -> None:
        """Start model."""
        self.settings = Settings()  # Please migrate from this
        dms_info(f"Loading Re-Ranker {self.settings} ON {self.settings}")

        self.model = CrossEncoder(
            self.settings.MODEL_NAME, device=self.settings.DEVICE, max_length=1024, model_kwargs={"torch_dtype": torch.bfloat16}
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
