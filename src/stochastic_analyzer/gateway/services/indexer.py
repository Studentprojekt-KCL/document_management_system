"""Document indexing and vector search service for Qdrant."""

import asyncio
import hashlib
from base64 import b64decode
from dataclasses import dataclass
from http import HTTPStatus
from io import BytesIO

import httpx
from markitdown import MarkItDown, StreamInfo
from markitdown._exceptions import (
    UnsupportedFormatException,
    FileConversionException,
    MissingDependencyException,
)

from shared_functions.dmis_logger import dms_warning
from shared_functions.initialisation_tools import read_env_variable, read_int_env_variable

_md = MarkItDown(enable_plugins=False)


def _to_uuid(pointer: str) -> str:
    """Hash a pointer string into a UUID for Qdrant."""
    h = hashlib.md5(pointer.encode()).hexdigest()
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
        """Construct an Indexer from environment variables."""
        config = IndexerConfig(
            embedding_url=read_env_variable("STOCHAN_EMBEDDING_URL"),
            qdrant_url=read_env_variable("STOCHAN_QDRANT_URL"),
            batch_size=read_int_env_variable("STOCHAN_INDEX_BATCH_SIZE"),
            max_chars=read_int_env_variable("STOCHAN_INDEX_MAX_CHARS"),
        )
        return cls(config=config, client=client)

    async def index(self, connector_url: str) -> dict:
        """Run the full indexing pipeline."""
        files = await self._fetch_files(connector_url)
        if not files:
            return {"status": "skipped", "reason": "no files or index not needed"}

        indexed = await self._embed_and_upsert(files)
        return {"status": "complete", "total": len(files), "indexed": indexed}

    async def search_similar(self, text: str, limit: int = 5) -> list[tuple[str, float]]:
        """Find the most similar documents in Qdrant for a given text."""
        resp = await self.client.post(
            f"{self.embedding_url}/embed",
            json={"inputs": [text[: self.max_chars]]},
            timeout=self.search_timeout,
        )
        resp.raise_for_status()
        vector = resp.json()[0]

        resp = await self.client.post(
            f"{self.qdrant_url}/collections/documents/points/query",
            json={"query": vector, "limit": limit, "with_payload": True},
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

    async def _extract_for_indexing(self, raw: bytes, name: str) -> str | None:
        """Extract markdown text via markitdown, truncated for embedding. None on failure."""
        try:
            result = await asyncio.to_thread(
                _md.convert_stream,
                BytesIO(raw),
                stream_info=StreamInfo(filename=name),
            )
        except (
            UnsupportedFormatException,
            FileConversionException,
            MissingDependencyException,
        ) as err:
            dms_warning(f"Failed to extract '{name}': {err}")
            return None
        content = result.text_content[: self.max_chars]
        return content if content.strip() else None

    async def _embed_and_upsert(self, files: list[dict]) -> int:
        """Embed documents and upsert them into Qdrant in batches."""
        await self._ensure_collection()

        indexed = 0
        for i in range(0, len(files), self.batch_size):
            batch = files[i : i + self.batch_size]

            texts, valid = [], []
            for f in batch:
                name = f.get("metadata", {}).get("name", "?")
                try:
                    raw = b64decode(f["content"])
                except (ValueError, KeyError):
                    dms_warning(f"Base64 decode failed: {name}")
                    continue
                content = await self._extract_for_indexing(raw, name)
                if content is None:
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
