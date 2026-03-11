import json
import httpx
from gateway.config import settings
from gateway.schemas import InputItem, ClassificationResult
from gateway.preprompts import CLASSIFIER_PROMPT

async def classify_document(item: InputItem) -> ClassificationResult | None:
    truncated_content = item.content[:1500]

    prompt = CLASSIFIER_PROMPT.format(
        name=item.metadata.name,
        author=item.metadata.author,
        content=truncated_content
    )

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