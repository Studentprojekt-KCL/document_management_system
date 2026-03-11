import json
import httpx
from gateway.config import Settings
from gateway.schemas import InputItem, ClassificationResult

settings = Settings()

async def classify_document(item: InputItem) -> ClassificationResult | None:
    truncated_content = item.content[:1500]

    prompt = f"""Name: {item.metadata.name}
Author: {item.metadata.author}
Content: {truncated_content}

You are a security classifier. 
Classify the document into exactly one of these security levels:
  Public       (no restrictions, safe for anyone)
  Internal     (for internal use only, not for public release)
  Sensitive    (restricted, limited distribution)
  Confidential (strictly restricted, serious risk if disclosed)

Return ONLY valid JSON: {{"Security-class": "<Public|Internal|Sensitive|Confidential>"}}"""

    payload = {
        "model": settings.QWEN_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.QWEN_URL, json=payload, timeout=60.0)
            response.raise_for_status()
            
            # Extract text, parse JSON directly, and return the Pydantic model
            data = json.loads(response.json().get("response", "{}"))
            return ClassificationResult(name=item.metadata.name, **data)
            
    except Exception as e:
        print(f"Classification failed for {item.metadata.name}: {e}")
        return None