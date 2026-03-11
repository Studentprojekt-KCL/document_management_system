"""Define API and routes"""

from fastapi import APIRouter, Request, HTTPException
from gateway.schemas import RankRequest, RankResponse, ScoredDocument, HealthCheck, InputItem, ClassificationResult, SummaryResult
from gateway.config import settings
from gateway.services.classifier import classify_document
from gateway.services.summarizer import summarize_documents
from gateway.services.ranker import rank_documents

router = APIRouter()

@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request) -> dict:
    """Health checks"""
    return {"status": "active", "model_loaded": True, "device": settings.DEVICE}


@router.post("/rerank", response_model=RankResponse)
async def rerank_documents(payload: RankRequest) -> dict:
    """Endpoint for the external TEI model."""
    if not payload.documents:
        return {"ranked_results": []}

    try:
        scores = await rank_documents(payload.query, payload.documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ranking engine failure: {str(e)}") from e

    scored_docs = sorted(
        [ScoredDocument(score=float(score), document=doc) for score, doc in zip(scores, payload.documents)],
        key=lambda x: x.score,
        reverse=True,
    )

    return {"ranked_results": scored_docs}

@router.post("/classify", response_model=list[ClassificationResult])
async def classify_documents(payload: list[InputItem]) -> list[dict]:
    results = []
    for item in payload:
        result = await classify_document(item)
        if result:
            results.append(result.model_dump(by_alias=True))
    return results

@router.post("/summarize", response_model=SummaryResult)
async def summarize_batch(payload: list[InputItem]) -> dict:
    """Endpoint to summarize a batch of documents into a single summary."""
    
    result = await summarize_documents(payload)
    
    if result:
        return result.model_dump()
    else:
        raise HTTPException(status_code=500, detail="Failed to generate a summary from the provided documents.")