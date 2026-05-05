"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the gateway indexer service.
"""

# Tests intentionally call private helpers on Indexer for focused checks.
# pylint: disable=protected-access

import base64
import hashlib
import unittest
import unittest.mock
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, call

import httpx

from gateway.services.indexer import Indexer, IndexerConfig, _to_uuid

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    embedding_url: str = "http://embed",
    qdrant_url: str = "http://qdrant",
    batch_size: int = 8,
    max_chars: int = 2000,
) -> IndexerConfig:
    return IndexerConfig(
        embedding_url=embedding_url,
        qdrant_url=qdrant_url,
        batch_size=batch_size,
        max_chars=max_chars,
    )


def _make_indexer(
    embedding_url: str = "http://embed",
    qdrant_url: str = "http://qdrant",
    batch_size: int = 8,
    max_chars: int = 2000,
) -> Indexer:
    """Return an Indexer with a mock async HTTP client."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    config = _make_config(
        embedding_url=embedding_url,
        qdrant_url=qdrant_url,
        batch_size=batch_size,
        max_chars=max_chars,
    )
    return Indexer(config=config, client=mock_client)


def _encode(text: str) -> str:
    """Base64-encode a string as the connector would return it."""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def _make_file(
    content: str = "document content",
    pointer: str = "https://gitlab.dms-lookup.com/api/v4/projects/7/repository/files/doc.txt",
    name: str = "doc.txt",
) -> dict:
    """Return a minimal file dict as returned by the connector."""
    return {
        "content": _encode(content),
        "metadata": {"unique_pointer": pointer, "name": name},
    }


def _mock_get(mock_client: AsyncMock, url_responses: dict) -> None:
    """Configure GET responses keyed by URL substring."""

    async def side_effect(url, **kwargs):
        for key, data in url_responses.items():
            if key in url:
                mock_resp = MagicMock()
                mock_resp.status_code = HTTPStatus.OK
                mock_resp.raise_for_status = MagicMock()
                mock_resp.json.return_value = data
                return mock_resp
        raise ValueError(f"Unexpected GET url: {url}")

    mock_client.get.side_effect = side_effect


def _mock_post(mock_client: AsyncMock, url_responses: dict) -> None:
    """Configure POST responses keyed by URL substring."""

    async def side_effect(url, **kwargs):
        for key, data in url_responses.items():
            if key in url:
                mock_resp = MagicMock()
                mock_resp.status_code = HTTPStatus.OK
                mock_resp.raise_for_status = MagicMock()
                mock_resp.json.return_value = data
                return mock_resp
        raise ValueError(f"Unexpected POST url: {url}")

    mock_client.post.side_effect = side_effect


# ---------------------------------------------------------------------------
# _to_uuid
# ---------------------------------------------------------------------------


class TestToUuid(unittest.TestCase):
    """Tests for the module-level _to_uuid helper."""

    def test_returns_valid_uuid_format(self) -> None:
        """Output matches the 8-4-4-4-12 UUID format."""
        result = _to_uuid("some-pointer")
        parts = result.split("-")
        self.assertEqual(len(parts), 5)
        self.assertEqual([len(p) for p in parts], [8, 4, 4, 4, 12])

    def test_same_input_gives_same_output(self) -> None:
        """Deterministic: same pointer always gives same UUID."""
        self.assertEqual(_to_uuid("ptr"), _to_uuid("ptr"))

    def test_different_inputs_give_different_uuids(self) -> None:
        """Different pointers produce different UUIDs."""
        self.assertNotEqual(_to_uuid("ptr-1"), _to_uuid("ptr-2"))

    def test_based_on_md5(self) -> None:
        """UUID is derived from the MD5 hex digest of the pointer."""
        h = hashlib.md5("ptr".encode()).hexdigest()
        expected = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
        self.assertEqual(_to_uuid("ptr"), expected)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestIndexerInit(unittest.TestCase):
    """Tests for Indexer.__init__."""

    def test_embedding_url_stored(self) -> None:
        ix = _make_indexer(embedding_url="http://my-embed")
        self.assertEqual(ix.embedding_url, "http://my-embed")

    def test_qdrant_url_stored(self) -> None:
        ix = _make_indexer(qdrant_url="http://my-qdrant")
        self.assertEqual(ix.qdrant_url, "http://my-qdrant")

    def test_batch_size_stored(self) -> None:
        ix = _make_indexer(batch_size=4)
        self.assertEqual(ix.batch_size, 4)

    def test_max_chars_stored(self) -> None:
        ix = _make_indexer(max_chars=500)
        self.assertEqual(ix.max_chars, 500)

    def test_client_stored(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        ix = Indexer(config=_make_config(), client=mock_client)
        self.assertIs(ix.client, mock_client)

    def test_class_level_timeouts(self) -> None:
        self.assertEqual(Indexer.index_timeout, 120.0)
        self.assertEqual(Indexer.search_timeout, 30.0)


# ---------------------------------------------------------------------------
# _build_points
# ---------------------------------------------------------------------------


class TestBuildPoints(unittest.TestCase):
    """Tests for Indexer._build_points."""

    def test_returns_one_point_per_file(self) -> None:
        files = [_make_file(pointer="ptr-1"), _make_file(pointer="ptr-2")]
        vectors = [[0.1, 0.2], [0.3, 0.4]]
        points = Indexer._build_points(files, vectors)
        self.assertEqual(len(points), 2)

    def test_point_contains_id_vector_payload(self) -> None:
        files = [_make_file(pointer="ptr-1")]
        vectors = [[0.1, 0.2]]
        point = Indexer._build_points(files, vectors)[0]
        self.assertIn("id", point)
        self.assertIn("vector", point)
        self.assertIn("payload", point)

    def test_id_is_uuid_of_pointer(self) -> None:
        pointer = "https://gitlab.dms-lookup.com/api/v4/projects/7/repository/files/doc.txt"
        files = [_make_file(pointer=pointer)]
        vectors = [[0.1]]
        point = Indexer._build_points(files, vectors)[0]
        self.assertEqual(point["id"], _to_uuid(pointer))

    def test_payload_contains_pointer_and_name(self) -> None:
        files = [_make_file(pointer="ptr-1", name="report.pdf")]
        vectors = [[0.1]]
        point = Indexer._build_points(files, vectors)[0]
        self.assertEqual(point["payload"]["unique_pointer"], "ptr-1")
        self.assertEqual(point["payload"]["name"], "report.pdf")

    def test_vector_matches_input(self) -> None:
        files = [_make_file()]
        vec = [0.1, 0.2, 0.3]
        point = Indexer._build_points(files, [vec])[0]
        self.assertEqual(point["vector"], vec)

    def test_missing_metadata_falls_back_to_empty_strings(self) -> None:
        files = [{"content": _encode("x")}]  # no metadata key
        vectors = [[0.1]]
        point = Indexer._build_points(files, vectors)[0]
        self.assertEqual(point["payload"]["unique_pointer"], "")
        self.assertEqual(point["payload"]["name"], "")


# ---------------------------------------------------------------------------
# _ensure_collection
# ---------------------------------------------------------------------------


class TestEnsureCollection(unittest.IsolatedAsyncioTestCase):
    """Tests for Indexer._ensure_collection."""

    async def test_no_create_when_collection_exists(self) -> None:
        """Skips creation when GET /collections/documents returns 200."""
        ix = _make_indexer()
        check_resp = MagicMock()
        check_resp.status_code = HTTPStatus.OK
        ix.client.get.return_value = check_resp

        await ix._ensure_collection()

        ix.client.put.assert_not_called()

    async def test_creates_collection_when_missing(self) -> None:
        """Calls PUT to create collection when GET returns non-200."""
        ix = _make_indexer()

        check_resp = MagicMock()
        check_resp.status_code = HTTPStatus.NOT_FOUND
        ix.client.get.return_value = check_resp

        probe_resp = MagicMock()
        probe_resp.raise_for_status = MagicMock()
        probe_resp.json.return_value = [[0.1, 0.2, 0.3]]  # dim=3
        ix.client.post.return_value = probe_resp

        put_resp = MagicMock()
        put_resp.raise_for_status = MagicMock()
        ix.client.put.return_value = put_resp

        await ix._ensure_collection()

        ix.client.put.assert_called_once()
        put_payload = ix.client.put.call_args[1]["json"]
        self.assertEqual(put_payload["vectors"]["size"], 3)

    async def test_collection_vector_distance_is_cosine(self) -> None:
        """Collection is created with Cosine distance."""
        ix = _make_indexer()

        check_resp = MagicMock()
        check_resp.status_code = HTTPStatus.NOT_FOUND
        ix.client.get.return_value = check_resp

        probe_resp = MagicMock()
        probe_resp.raise_for_status = MagicMock()
        probe_resp.json.return_value = [[0.1, 0.2]]
        ix.client.post.return_value = probe_resp

        put_resp = MagicMock()
        put_resp.raise_for_status = MagicMock()
        ix.client.put.return_value = put_resp

        await ix._ensure_collection()

        put_payload = ix.client.put.call_args[1]["json"]
        self.assertEqual(put_payload["vectors"]["distance"], "Cosine")


# ---------------------------------------------------------------------------
# _fetch_files
# ---------------------------------------------------------------------------


class TestFetchFiles(unittest.IsolatedAsyncioTestCase):
    """Tests for Indexer._fetch_files."""

    async def test_returns_empty_when_index_not_needed(self) -> None:
        """Returns [] when manifest says index_needed=False."""
        ix = _make_indexer()
        _mock_get(ix.client, {"files_to_index": {"index_needed": False, "file_url": "http://files"}})
        result = await ix._fetch_files("http://connector")
        self.assertEqual(result, [])

    async def test_returns_files_when_index_needed(self) -> None:
        """Returns file list when index_needed=True."""
        ix = _make_indexer()
        files = [_make_file()]
        _mock_get(
            ix.client,
            {
                "files_to_index": {"index_needed": True, "file_url": "http://files"},
                "http://files": {"files": files},
            },
        )
        result = await ix._fetch_files("http://connector")
        self.assertEqual(result, files)

    async def test_trailing_slash_stripped_from_connector_url(self) -> None:
        """Trailing slash in connector_url is stripped."""
        ix = _make_indexer()
        _mock_get(ix.client, {"files_to_index": {"index_needed": False, "file_url": "http://files"}})
        await ix._fetch_files("http://connector/")
        called_url = ix.client.get.call_args_list[0][0][0]
        self.assertFalse(called_url.endswith("//files_to_index"))


# ---------------------------------------------------------------------------
# search_similar
# ---------------------------------------------------------------------------


class TestSearchSimilar(unittest.IsolatedAsyncioTestCase):
    """Tests for Indexer.search_similar."""

    def _setup_search(self, ix: Indexer, vector: list[float], points: list[dict]) -> None:
        """Configure mocks for a search_similar call."""
        embed_resp = MagicMock()
        embed_resp.raise_for_status = MagicMock()
        embed_resp.json.return_value = [vector]

        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {"result": {"points": points}}

        ix.client.post.side_effect = [embed_resp, search_resp]

    async def test_returns_pointer_score_tuples(self) -> None:
        """Returns list of (unique_pointer, score) tuples."""
        ix = _make_indexer()
        self._setup_search(
            ix,
            [0.1, 0.2],
            [
                {"payload": {"unique_pointer": "ptr-1"}, "score": 0.9},
                {"payload": {"unique_pointer": "ptr-2"}, "score": 0.7},
            ],
        )
        result = await ix.search_similar("some text")
        self.assertEqual(result, [("ptr-1", 0.9), ("ptr-2", 0.7)])

    async def test_skips_points_without_pointer(self) -> None:
        """Points missing unique_pointer in payload are excluded."""
        ix = _make_indexer()
        self._setup_search(
            ix,
            [0.1],
            [
                {"payload": {}, "score": 0.9},
                {"payload": {"unique_pointer": "ptr-1"}, "score": 0.8},
            ],
        )
        result = await ix.search_similar("text")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "ptr-1")

    async def test_empty_results_returns_empty_list(self) -> None:
        """Returns [] when Qdrant returns no points."""
        ix = _make_indexer()
        self._setup_search(ix, [0.1], [])
        result = await ix.search_similar("text")
        self.assertEqual(result, [])

    async def test_embed_called_with_truncated_text(self) -> None:
        """Text sent to embedding is truncated to max_chars."""
        ix = _make_indexer(max_chars=10)
        self._setup_search(ix, [0.1], [])
        await ix.search_similar("A" * 100)
        embed_payload = ix.client.post.call_args_list[0][1]["json"]
        self.assertEqual(embed_payload["inputs"], ["A" * 10])

    async def test_qdrant_queried_with_limit(self) -> None:
        """Qdrant query includes the requested limit."""
        ix = _make_indexer()
        self._setup_search(ix, [0.1], [])
        await ix.search_similar("text", limit=3)
        qdrant_payload = ix.client.post.call_args_list[1][1]["json"]
        self.assertEqual(qdrant_payload["limit"], 3)


# ---------------------------------------------------------------------------
# index (integration of _fetch_files + _embed_and_upsert)
# ---------------------------------------------------------------------------


class TestIndex(unittest.IsolatedAsyncioTestCase):
    """Tests for Indexer.index."""

    async def test_returns_skipped_when_no_files(self) -> None:
        """Returns skipped status when connector reports index not needed."""
        ix = _make_indexer()
        _mock_get(ix.client, {"files_to_index": {"index_needed": False, "file_url": "http://files"}})
        result = await ix.index("http://connector")
        self.assertEqual(result["status"], "skipped")

    async def test_returns_complete_with_counts(self) -> None:
        """Returns complete status with total and indexed counts."""
        ix = _make_indexer()
        files = [_make_file(pointer=f"ptr-{i}") for i in range(2)]

        _mock_get(
            ix.client,
            {
                "files_to_index": {"index_needed": True, "file_url": "http://files"},
                "http://files": {"files": files},
                "collections/documents": {},  # collection exists
            },
        )

        check_resp = MagicMock()
        check_resp.status_code = HTTPStatus.OK
        ix.client.get.side_effect = None

        async def get_side(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if "files_to_index" in url:
                resp.json.return_value = {"index_needed": True, "file_url": "http://files"}
            elif "http://files" in url:
                resp.json.return_value = {"files": files}
            elif "collections/documents" in url:
                resp.status_code = HTTPStatus.OK
            resp.status_code = HTTPStatus.OK
            return resp

        ix.client.get.side_effect = get_side

        embed_resp = MagicMock()
        embed_resp.raise_for_status = MagicMock()
        embed_resp.json.return_value = [[0.1, 0.2]] * 2

        put_resp = MagicMock()
        put_resp.raise_for_status = MagicMock()

        ix.client.post.return_value = embed_resp
        ix.client.put.return_value = put_resp

        result = await ix.index("http://connector")

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["indexed"], 2)

    async def test_invalid_base64_files_are_skipped(self) -> None:
        """Files with invalid base64 content are skipped with a warning."""
        ix = _make_indexer()
        bad_file = {"content": "!!!bad-base64!!!", "metadata": {"unique_pointer": "ptr-bad", "name": "bad.txt"}}
        good_file = _make_file(pointer="ptr-good")

        async def get_side(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.status_code = HTTPStatus.OK
            if "files_to_index" in url:
                resp.json.return_value = {"index_needed": True, "file_url": "http://files"}
            else:
                resp.json.return_value = {"files": [bad_file, good_file]}
            return resp

        ix.client.get.side_effect = get_side

        embed_resp = MagicMock()
        embed_resp.raise_for_status = MagicMock()
        embed_resp.json.return_value = [[0.1, 0.2]]

        put_resp = MagicMock()
        put_resp.raise_for_status = MagicMock()

        ix.client.post.return_value = embed_resp
        ix.client.put.return_value = put_resp

        with unittest.mock.patch("gateway.services.indexer.dms_warning") as mock_warn:
            result = await ix.index("http://connector")

        mock_warn.assert_called_once()
        self.assertEqual(result["indexed"], 1)  # only the good file
