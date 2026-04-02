"""Ranking logic for external TEI model."""

import asyncio
import httpx


async def rank_documents(query: str, texts: list[str], tei_url: str, batch_size: int = 250, max_chars: int = 3000) -> list[float]:
    """Send texts to the TEI container for semantic reranking in safe, parallel batches."""
    if not texts:
        return []

    all_scores = [0.0] * len(texts)

    async def fetch_batch(client: httpx.AsyncClient, start_idx: int, batch: list[str]) -> None:
        truncated = [text[:max_chars] for text in batch]
        response = await client.post(tei_url, json={"query": query, "texts": truncated}, timeout=60.0)
        response.raise_for_status()

        for res in response.json():
            idx = res.get("index")
            score = res.get("score")
            if idx is not None and score is not None:
                all_scores[start_idx + idx] = float(score)

    async with httpx.AsyncClient() as client:
        tasks = [fetch_batch(client, i, texts[i : i + batch_size]) for i in range(0, len(texts), batch_size)]
        await asyncio.gather(*tasks)

    return all_scores
