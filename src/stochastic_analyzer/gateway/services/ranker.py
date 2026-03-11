"""Ranking logic for external TEI model."""

import httpx
from gateway.config import settings
from gateway.schemas import DocumentObject
from dmis_logger import dms_info

async def rank_documents(query: str, documents: list[DocumentObject]) -> list[float]:
    """Sends documents to the TEI container for semantic reranking."""
    if not documents:
        return []

    # TEI expects a list of strings mapped to 'texts'
    texts = [f"{doc.title} {doc.content}"[:1024] for doc in documents]
    
    payload = {
        "query": query,
        "texts": texts
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.TEI_URL, json=payload, timeout=30.0)
            response.raise_for_status()
            
            results = response.json()
            
            results_sorted = sorted(results, key=lambda x: x["index"])
            return [float(res["score"]) for res in results_sorted]
            
    except Exception as e:
        dms_info(f"TEI Reranker failed: {e}")
        raise e