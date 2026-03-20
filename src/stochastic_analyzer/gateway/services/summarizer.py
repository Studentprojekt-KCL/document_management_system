import httpx
from json.decoder import JSONDecodeError
from gateway.config import Settings
from gateway.schemas import InputItem, SummaryResult
from gateway.preprompts import SUMMARIZER_PROMPT
from dmis_logger import dms_warning

async def summarize_documents(items: list[InputItem]) -> SummaryResult | None:
    settings = Settings() #Please migrate from this
    combined_context = ""
    for i, item in enumerate(items, 1):
        doc_name = item.metadata.name or f"Document {i}"
        combined_context += f"\n--- {doc_name} ---\n{item.content}\n"

    prompt = SUMMARIZER_PROMPT.format(combined_context=combined_context)

    payload = {
        "model": settings.MINISTRAL_MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.MINISTRAL_URL, json=payload, timeout=120)
            response.raise_for_status()
            summary_text = response.json().get("response", "").strip()
            return SummaryResult(summary=summary_text)
    except httpx.HTTPStatusError as err:
        dms_warning(f"Unexpected response (status code {response.status_code}) from {settings.MINISTRAL_URL}, {err}")
    except JSONDecodeError as err:
        dms_warning(f"Response from {settings.MINISTRAL_URL} could not be decoded, {err}")
    except httpx.TimeoutException as err:
        dms_warning(f"Connection to {settings.MINISTRAL_URL} timed out, {err}")
    return None
