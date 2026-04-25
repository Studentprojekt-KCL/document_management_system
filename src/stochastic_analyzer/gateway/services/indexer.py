"""Document indexing and vector search service for Qdrant."""

import hashlib
from base64 import b64decode
from dataclasses import dataclass
from http import HTTPStatus
from os import environ

import httpx

from shared_functions.dmis_logger import dms_error, dms_warning
from shared_functions.initialisation_tools import read_env_variable


def _to_uuid(pointer: str) -> str:
    """Hash a pointer string into a UUID for Qdrant."""
    h = hashlib.md5(pointer.encode()).hexdigest()
    # Slice the 32-char hex digest into some super cool groups for vector db support
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


@dataclass
class IndexerConfig:
    """Configuration settings for the Indexer service."""

    embedding_url: str
    qdrant_url: str
    batch_size: int = 8
    max_chars: int = 2000


class Indexer:
    """Document indexer and vector search using Qdrant and TEI embeddings.

    Attributes:
        embedding_url: URL for the TEI embedding container.
        qdrant_url: URL for the Qdrant vector database.
        client: Shared async HTTP client.
        batch_size: Number of documents embedded per batch.
        max_chars: Maximum characters per document sent for embedding.
        index_timeout: Per-request timeout for indexing operations.
        search_timeout: Per-request timeout for similarity search.
    """

    index_timeout: float = 120.0
    search_timeout: float = 30.0

    def __init__(self, config: IndexerConfig, client: httpx.AsyncClient) -> None:
        self.embedding_url = config.embedding_url
        self.qdrant_url = config.qdrant_url
        self.batch_size = config.batch_size
        self.max_chars = config.max_chars
        self.client = client

    @classmethod
    def from_env(cls, client: httpx.AsyncClient) -> "Indexer":
        """Construct an Indexer from environment variables.

        Reads (required):
            STOCHAN_EMBEDDING_URL: URL for the TEI embedding container.
            STOCHAN_QDRANT_URL: URL for the Qdrant vector database.

        Reads (optional):
            INDEX_BATCH_SIZE: Documents embedded per batch (default 8).
            STOCHAN_INDEX_MAX_CHARS: Max characters per document (default 2000).

        Raises:
            RuntimeError: If any required variable is missing.
        """
        embedding_url = read_env_variable("STOCHAN_EMBEDDING_URL")
        qdrant_url = read_env_variable("STOCHAN_QDRANT_URL")

        missing = [
            name
            for name, value in (
                ("STOCHAN_EMBEDDING_URL", embedding_url),
                ("STOCHAN_QDRANT_URL", qdrant_url),
            )
            if value is None
        ]
        if missing:
            dms_error(f"Indexer env vars not defined: {', '.join(missing)}")
            raise RuntimeError(f"Missing env vars: {missing}")

        config = IndexerConfig(
            embedding_url=embedding_url,
            qdrant_url=qdrant_url,
            batch_size=int(environ.get("INDEX_BATCH_SIZE", "8")),
            max_chars=int(environ.get("STOCHAN_INDEX_MAX_CHARS", "2000")),
        )
        return cls(config=config, client=client)

    async def index(self, connector_url: str) -> dict:
        """Run the full indexing pipeline.

        Returns:
            Status dict with total file count and indexed count.
        """
        files = await self._fetch_files(connector_url)
        if not files:
            return {"status": "skipped", "reason": "no files or index not needed"}

        indexed = await self._embed_and_upsert(files)
        return {"status": "complete", "total": len(files), "indexed": indexed}

    async def search_similar(self, text: str, limit: int = 5) -> list[tuple[str, float]]:
        """Find the most similar documents in Qdrant for a given text.

        Args:
            text: reference document content.
            limit: number of candidates to return.

        Returns:
            List of (unique_pointer, score) tuples for the top matches.
        """
        resp = await self.client.post(
            f"{self.embedding_url}/embed",
            json={"inputs": [text[: self.max_chars]]},
            timeout=self.search_timeout,
        )
        resp.raise_for_status()
        vector = resp.json()[0]

        resp = await self.client.post(
            f"{self.qdrant_url}/collections/documents/points/query",
            json={
                "query": vector,
                "limit": limit,
                "with_payload": True,
            },
            timeout=self.search_timeout,
        )
        resp.raise_for_status()
        points = resp.json().get("result", {}).get("points", [])

        return [(p["payload"]["unique_pointer"], p["score"]) for p in points if p.get("payload", {}).get("unique_pointer")]

    async def _fetch_files(self, connector_url: str) -> list[dict]:
        """Get the file list from the connector's indexing endpoint."""
        resp = await self.client.get(
            f"{connector_url.rstrip('/')}/files_to_index",
            timeout=self.index_timeout,
        )
        resp.raise_for_status()
        manifest = resp.json()

        if not manifest.get("index_needed", False):
            return []

        resp = await self.client.get(manifest["file_url"], timeout=self.index_timeout)
        resp.raise_for_status()
        return resp.json().get("files", [])

    @staticmethod
    def _build_points(valid: list[dict], vectors: list[list[float]]) -> list[dict]:
        """Build Qdrant point dicts from file metadata and vectors."""
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
        return points

    async def _ensure_collection(self) -> None:
        """Create the Qdrant collection if missing, probing for vector dimension."""
        check = await self.client.get(
            f"{self.qdrant_url}/collections/documents",
            timeout=self.index_timeout,
        )
        if check.status_code == HTTPStatus.OK:
            return

        probe = await self.client.post(
            f"{self.embedding_url}/embed",
            json={"inputs": ["x"]},
            timeout=self.index_timeout,
        )
        probe.raise_for_status()
        size = len(probe.json()[0])

        await self.client.put(
            f"{self.qdrant_url}/collections/documents",
            json={"vectors": {"size": size, "distance": "Cosine"}},
            timeout=self.index_timeout,
        )

    async def _embed_and_upsert(self, files: list[dict]) -> int:
        """Embed documents and upsert them into Qdrant in batches."""
        await self._ensure_collection()

        indexed = 0
        for i in range(0, len(files), self.batch_size):
            batch = files[i : i + self.batch_size]

            texts, valid = [], []
            for f in batch:
                try:
                    content = b64decode(f["content"]).decode("utf-8")[: self.max_chars]
                except (UnicodeDecodeError, ValueError, KeyError):
                    dms_warning(f"Failed to decode: {f.get('metadata', {}).get('name', '?')}")
                    continue
                if not content.strip():
                    continue
                texts.append(content)
                valid.append(f)

            if not texts:
                continue

            resp = await self.client.post(
                f"{self.embedding_url}/embed",
                json={"inputs": texts},
                timeout=self.index_timeout,
            )
            resp.raise_for_status()
            vectors = resp.json()

            points = self._build_points(valid, vectors)

            await self.client.put(
                f"{self.qdrant_url}/collections/documents/points",
                json={"points": points},
                timeout=self.index_timeout,
            )
            indexed += len(points)

        return indexed
