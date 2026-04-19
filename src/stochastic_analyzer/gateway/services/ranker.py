"""Ranking logic for external TEI model."""

import asyncio

import httpx


class Ranker:
    """Semantic document ranker using an external TEI reranker.

    Attributes:
        url: URL for the TEI reranker endpoint.
        batch_size: Number of texts per batch request.
        max_chars: Maximum characters per text for ranking.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        url: str,
        batch_size: int = 250,
        max_chars: int = 3000,
        timeout: float = 60.0,
    ) -> None:
        self.url = url
        self.batch_size = batch_size
        self.max_chars = max_chars
        self.timeout = timeout

    async def rank(self, query: str, texts: list[str]) -> list[float]:
        """Send texts to the TEI container for semantic reranking in parallel batches."""
        if not texts:
            return []

        all_scores = [0.0] * len(texts)

        async def fetch_batch(client: httpx.AsyncClient, start_idx: int, batch: list[str]) -> None:
            truncated = [text[: self.max_chars] for text in batch]
            response = await client.post(
                self.url,
                json={"query": query, "texts": truncated},
                timeout=self.timeout,
            )
            response.raise_for_status()

            for res in response.json():
                idx = res.get("index")
                score = res.get("score")
                if idx is not None and score is not None:
                    all_scores[start_idx + idx] = float(score)

        async with httpx.AsyncClient() as client:
            tasks = [fetch_batch(client, i, texts[i : i + self.batch_size]) for i in range(0, len(texts), self.batch_size)]
            await asyncio.gather(*tasks)

        return all_scores
