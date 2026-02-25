"""Define API and routes"""

from fastapi import APIRouter, Request, HTTPException
from .schemas import RankRequest, RankResponse, ScoredDocument, HealthCheck
from .config import settings

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request) -> dict:
    """Health checks"""

    model_loaded = hasattr(request.app.state, "model") and request.app.state.model is not None
    return {"status": "active", "model_loaded": model_loaded, "device": settings.DEVICE}


@router.post("/rerank", response_model=RankResponse)
async def rerank_documents(request: Request, payload: RankRequest) -> dict:
    """Endpoint for the embedded model."""
    if not payload.documents:
        return {"ranked_results": []}

    try:
        scores = request.app.state.model.rank(payload.query, payload.documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ranking engine failure: {str(e)}") from e

    scored_docs = sorted(
        [ScoredDocument(score=float(score), document=doc) for score, doc in zip(scores, payload.documents)],
        key=lambda x: x.score,
        reverse=True,
    )

    return {"ranked_results": scored_docs}
