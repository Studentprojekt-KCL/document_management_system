"""Ranking logic for external TEI model."""

import httpx
import asyncio
from gateway.config import Settings
from gateway.schemas import DocumentObject
from dmis_logger import dms_info
settings = Settings()

async def rank_documents(query: str, documents: list[DocumentObject]) -> list[float]:
    """Sends documents to the TEI container for semantic reranking in safe, parallel batches."""
    if not documents:
        return []

    batch_size = getattr(settings, 'TEI_BATCH_SIZE', 250)
    max_chars = getattr(settings, 'TEI_MAX_CHARS', 3000)
    all_scores = [0.0] * len(documents)

    async def fetch_batch(client: httpx.AsyncClient, start_idx: int, batch: list[DocumentObject]):
        texts = [f"{doc.title} {doc.content}"[:max_chars] for doc in batch]
        response = await client.post(settings.TEI_URL, json={"query": query, "texts": texts}, timeout=60.0)
        response.raise_for_status()

        for res in response.json():
            all_scores[start_idx + res["index"]] = float(res["score"])

    async with httpx.AsyncClient() as client:
        tasks = [fetch_batch(client, i, documents[i : i + batch_size]) for i in range(0, len(documents), batch_size)]
        await asyncio.gather(*tasks)

    return all_scores
