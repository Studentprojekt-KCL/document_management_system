import httpx
from gateway.config import Settings
from gateway.schemas import InputItem, SummaryResult

settings = Settings()
async def summarize_documents(items: list[InputItem]) -> SummaryResult | None:
    
    combined_context = ""
    for i, item in enumerate(items, 1):
        doc_name = item.metadata.name or f"Document {i}"
        combined_context += f"\n--- {doc_name} ---\n{item.content}\n"

    prompt = f"""Please provide a comprehensive, single summary based on the following batch of documents.
    
Documents:
{combined_context}
    
Unified Summary:"""

    payload = {
        "model": settings.MINISTRAL_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.MINISTRAL_URL, json=payload, timeout=90.0)
            response.raise_for_status()
            
            summary_text = response.json().get("response", "").strip()
            return SummaryResult(summary=summary_text)
            
    except Exception as e:
        print(f"Batch summarization failed: {e}")
        return None
