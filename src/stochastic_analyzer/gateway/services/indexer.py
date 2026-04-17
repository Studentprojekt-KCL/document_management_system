"""Document indexing and vector search service for Qdrant."""

import hashlib
from base64 import b64decode

import httpx

from dmis_logger import dms_warning

COLLECTION = "documents"
VECTOR_SIZE = 384
BATCH_SIZE = 8
MAX_CHARS = 2000
HTTP_OK = 200


def _to_uuid(pointer: str) -> str:
    """Hash a pointer string into a UUID for Qdrant."""
    h = hashlib.md5(pointer.encode()).hexdigest()  # noqa: S324
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


class Indexer:
    """Document indexer and vector search using Qdrant and TEI embeddings.

    Attributes:
        embedding_url: URL for the TEI embedding container.
        qdrant_url: URL for the Qdrant vector database.
    """

    def __init__(self, embedding_url: str, qdrant_url: str) -> None:
        self.embedding_url = embedding_url
        self.qdrant_url = qdrant_url

    async def index(self, connector_url: str) -> dict:
        """Run the full indexing pipeline.

        Returns:
            Status dict with total file count and indexed count.
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = await self._fetch_files(connector_url, client)
            if not files:
                return {"status": "skipped", "reason": "no files or index not needed"}

            indexed = await self._embed_and_upsert(files, client)

        return {"status": "complete", "total": len(files), "indexed": indexed}

    async def search_similar(self, text: str, limit: int = 50) -> list[str]:
        """Find the most similar documents in Qdrant for a given text.

        Args:
            text: reference document content.
            limit: number of candidates to return.

        Returns:
            List of unique_pointers for the top matches.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.embedding_url}/embed",
                json={"inputs": [text[:MAX_CHARS]]},
            )
            resp.raise_for_status()
            vector = resp.json()[0]

            resp = await client.post(
                f"{self.qdrant_url}/collections/{COLLECTION}/points/query",
                json={
                    "query": vector,
                    "limit": limit,
                    "with_payload": True,
                },
            )
            resp.raise_for_status()
            points = resp.json().get("result", {}).get("points", [])

        return [p["payload"]["unique_pointer"] for p in points if p.get("payload", {}).get("unique_pointer")]

    async def _fetch_files(self, connector_url: str, client: httpx.AsyncClient) -> list[dict]:
        """Get the file list from the connector's indexing endpoint."""
        resp = await client.get(f"{connector_url.rstrip('/')}/files_to_index")
        resp.raise_for_status()
        manifest = resp.json()

        if not manifest.get("index_needed", False):
            return []

        resp = await client.get(manifest["file_url"])
        resp.raise_for_status()
        return resp.json().get("files", [])

    async def _embed_and_upsert(self, files: list[dict], client: httpx.AsyncClient) -> int:
        """Embed documents and upsert them into Qdrant in batches."""
        check = await client.get(f"{self.qdrant_url}/collections/{COLLECTION}")
        if check.status_code != HTTP_OK:
            await client.put(
                f"{self.qdrant_url}/collections/{COLLECTION}",
                json={"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}},
            )

        indexed = 0
        for i in range(0, len(files), BATCH_SIZE):
            batch = files[i : i + BATCH_SIZE]

            texts, valid = [], []
            for f in batch:
                try:
                    content = b64decode(f["content"]).decode("utf-8")[:MAX_CHARS]
                except (UnicodeDecodeError, ValueError, KeyError):
                    dms_warning(f"Failed to decode: {f.get('metadata', {}).get('name', '?')}")
                    continue
                if not content.strip():
                    continue
                texts.append(content)
                valid.append(f)

            if not texts:
                continue

            resp = await client.post(f"{self.embedding_url}/embed", json={"inputs": texts})
            resp.raise_for_status()
            vectors = resp.json()

            points = []
            for f, vec in zip(valid, vectors, strict=True):
                meta = f.get("metadata", {})
                pointer = meta.get("unique_pointer", "")
                points.append(
                    {
                        "id": _to_uuid(pointer),
                        "vector": vec,
                        "payload": {
                            "unique_pointer": pointer,
                            "name": meta.get("name", ""),
                        },
                    }
                )

            await client.put(
                f"{self.qdrant_url}/collections/{COLLECTION}/points",
                json={"points": points},
            )
            indexed += len(points)

        return indexed
