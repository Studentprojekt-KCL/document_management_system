"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the gateway API routes.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway.schemas import (
    ClassificationResult,
    InputItem,
    MetadataTemplate,
    SummaryResult,
)
from gateway.services.classifier import LABELS
from gateway.routes import Services, create_router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GITLAB_POINTER = "https://gitlab.dms-lookup.com/api/v4/projects/7/repository/files/doc.txt"
GITLAB_POINTER_2 = "https://gitlab.dms-lookup.com/api/v4/projects/6/repository/files/other.md"


def _make_item(
    content: str = "Some document content.",
    name: str = "doc.txt",
    pointer: str = GITLAB_POINTER,
) -> InputItem:
    return InputItem(
        content=content,
        metadata=MetadataTemplate(name=name, unique_pointer=pointer),
    )


def _make_services(
    connector=None,
    summarizer=None,
    classifier=None,
    pdf_converter=None,
    indexer=None,
) -> Services:
    """Return a Services dataclass with AsyncMock defaults for each service."""
    return Services(
        connector=connector or AsyncMock(),
        summarizer=summarizer or AsyncMock(),
        classifier=classifier or AsyncMock(),
        pdf_converter=pdf_converter or MagicMock(),
        indexer=indexer or AsyncMock(),
    )


def _make_client(services: Services, device: str = "cpu") -> TestClient:
    """Wire up a FastAPI app with the given services and return a test client."""
    app = FastAPI()
    app.include_router(create_router(services, device=device))
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealthCheck(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client(_make_services(), device="cuda")

    def test_returns_200(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)

    def test_response_contains_status_active(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.json()["status"], "active")

    def test_response_contains_device(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.json()["device"], "cuda")

    def test_model_loaded_is_true(self) -> None:
        resp = self.client.get("/health")
        self.assertTrue(resp.json()["model_loaded"])


# ---------------------------------------------------------------------------
# GET /classifications
# ---------------------------------------------------------------------------


class TestClassifications(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client(_make_services())

    def test_returns_200(self) -> None:
        resp = self.client.get("/classifications")
        self.assertEqual(resp.status_code, 200)

    def test_returns_labels_list(self) -> None:
        resp = self.client.get("/classifications")
        self.assertEqual(resp.json(), LABELS)


# ---------------------------------------------------------------------------
# POST /classify
# ---------------------------------------------------------------------------


class TestClassifyEndpoint(unittest.TestCase):
    def test_returns_200_with_results(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        classifier = AsyncMock()
        classifier.classify.return_value = [ClassificationResult(unique_pointer=GITLAB_POINTER, security_class="Internal")]

        client = _make_client(_make_services(connector=connector, classifier=classifier))
        resp = client.post("/classify", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 200)

    def test_returns_classification_results(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        classifier = AsyncMock()
        classifier.classify.return_value = [ClassificationResult(unique_pointer=GITLAB_POINTER, security_class="Confidential")]

        client = _make_client(_make_services(connector=connector, classifier=classifier))
        resp = client.post("/classify", json={"pointers": [GITLAB_POINTER]})
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["Security-class"], "Confidential")

    def test_returns_502_when_connector_fails(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = []

        client = _make_client(_make_services(connector=connector))
        resp = client.post("/classify", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 502)

    def test_classifier_called_with_items(self) -> None:
        connector = AsyncMock()
        items = [_make_item()]
        connector.get_file_contents.return_value = items

        classifier = AsyncMock()
        classifier.classify.return_value = [ClassificationResult(unique_pointer=GITLAB_POINTER, security_class="Public")]

        client = _make_client(_make_services(connector=connector, classifier=classifier))
        client.post("/classify", json={"pointers": [GITLAB_POINTER]})
        classifier.classify.assert_called_once_with(items)


# ---------------------------------------------------------------------------
# POST /summarize
# ---------------------------------------------------------------------------


class TestSummarizeEndpoint(unittest.TestCase):
    def test_returns_200_with_summary(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = SummaryResult(summary="A nice summary.")

        client = _make_client(_make_services(connector=connector, summarizer=summarizer))
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "A nice summary.")

    def test_returns_502_when_connector_fails(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = []

        client = _make_client(_make_services(connector=connector))
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 502)

    def test_returns_500_when_summarizer_fails(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = None

        client = _make_client(_make_services(connector=connector, summarizer=summarizer))
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 500)

    def test_multiple_pointers_all_fetched(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item(), _make_item(pointer=GITLAB_POINTER_2)]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = SummaryResult(summary="Combined summary.")

        client = _make_client(_make_services(connector=connector, summarizer=summarizer))
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]})
        self.assertEqual(resp.status_code, 200)
        connector.get_file_contents.assert_called_once_with([GITLAB_POINTER, GITLAB_POINTER_2])


# ---------------------------------------------------------------------------
# POST /index
# ---------------------------------------------------------------------------


class TestIndexEndpoint(unittest.TestCase):
    def test_returns_index_result(self) -> None:
        indexer = AsyncMock()
        indexer.index.return_value = {"status": "complete", "total": 5, "indexed": 5}

        connector = AsyncMock()
        connector.url = "http://connector"

        client = _make_client(_make_services(connector=connector, indexer=indexer))
        resp = client.post("/index")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "complete")

    def test_index_called_with_connector_url(self) -> None:
        indexer = AsyncMock()
        indexer.index.return_value = {"status": "skipped", "reason": "no files or index not needed"}

        connector = AsyncMock()
        connector.url = "http://connector"

        client = _make_client(_make_services(connector=connector, indexer=indexer))
        client.post("/index")
        indexer.index.assert_called_once_with("http://connector")


# ---------------------------------------------------------------------------
# POST /rerank
# ---------------------------------------------------------------------------


class TestRerankEndpoint(unittest.TestCase):
    def test_returns_400_for_multiple_pointers(self) -> None:
        client = _make_client(_make_services())
        resp = client.post("/rerank", json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]})
        self.assertEqual(resp.status_code, 400)

    def test_returns_422_for_empty_pointers(self) -> None:
        """Empty pointers list is rejected by schema validation before the route runs."""
        client = _make_client(_make_services())
        resp = client.post("/rerank", json={"pointers": []})
        self.assertEqual(resp.status_code, 422)

    def test_returns_502_when_reference_doc_not_found(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = []

        client = _make_client(_make_services(connector=connector))
        resp = client.post("/rerank", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 502)

    def test_returns_empty_ranked_results_when_no_similar(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        indexer = AsyncMock()
        indexer.search_similar.return_value = []

        client = _make_client(_make_services(connector=connector, indexer=indexer))
        resp = client.post("/rerank", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["ranked_results"], [])

    def test_excludes_query_pointer_from_results(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]
        connector.get_file_metadata.return_value = [
            {"unique_pointer": GITLAB_POINTER_2, "name": "other.md", "last_edit_date": "2026-01-01"}
        ]

        indexer = AsyncMock()
        # Returns both the query pointer and another — query pointer must be filtered out
        indexer.search_similar.return_value = [
            (GITLAB_POINTER, 1.0),
            (GITLAB_POINTER_2, 0.8),
        ]

        client = _make_client(_make_services(connector=connector, indexer=indexer))
        resp = client.post("/rerank", json={"pointers": [GITLAB_POINTER]})
        results = resp.json()["ranked_results"]
        pointers = [r["unique_pointer"] for r in results]
        self.assertNotIn(GITLAB_POINTER, pointers)
        self.assertIn(GITLAB_POINTER_2, pointers)

    def test_results_sorted_by_score_descending(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]
        connector.get_file_metadata.return_value = [
            {"unique_pointer": "ptr-a", "name": "a.txt", "last_edit_date": "2026-01-01"},
            {"unique_pointer": "ptr-b", "name": "b.txt", "last_edit_date": "2026-01-01"},
        ]

        indexer = AsyncMock()
        indexer.search_similar.return_value = [
            ("ptr-a", 0.6),
            ("ptr-b", 0.9),
        ]

        client = _make_client(_make_services(connector=connector, indexer=indexer))
        resp = client.post("/rerank", json={"pointers": [GITLAB_POINTER]})
        scores = [r["score"] for r in resp.json()["ranked_results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ---------------------------------------------------------------------------
# POST /md-to-pdf
# ---------------------------------------------------------------------------


class TestMdToPdfEndpoint(unittest.TestCase):
    def test_returns_pdf_content_type(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = SummaryResult(summary="Summary text.")

        pdf_converter = MagicMock()
        pdf_converter.convert.return_value = b"%PDF-fake-bytes"

        client = _make_client(
            _make_services(
                connector=connector,
                summarizer=summarizer,
                pdf_converter=pdf_converter,
            )
        )
        resp = client.post("/md-to-pdf", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/pdf")

    def test_returns_pdf_bytes(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = SummaryResult(summary="Summary text.")

        pdf_converter = MagicMock()
        pdf_converter.convert.return_value = b"%PDF-fake-bytes"

        client = _make_client(
            _make_services(
                connector=connector,
                summarizer=summarizer,
                pdf_converter=pdf_converter,
            )
        )
        resp = client.post("/md-to-pdf", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.content, b"%PDF-fake-bytes")

    def test_returns_502_when_connector_fails(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = []

        client = _make_client(_make_services(connector=connector))
        resp = client.post("/md-to-pdf", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 502)

    def test_returns_500_when_summarizer_fails(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = None

        client = _make_client(_make_services(connector=connector, summarizer=summarizer))
        resp = client.post("/md-to-pdf", json={"pointers": [GITLAB_POINTER]})
        self.assertEqual(resp.status_code, 500)

    def test_pdf_converter_called_with_summary_text(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = SummaryResult(summary="The summary.")

        pdf_converter = MagicMock()
        pdf_converter.convert.return_value = b"%PDF"

        client = _make_client(
            _make_services(
                connector=connector,
                summarizer=summarizer,
                pdf_converter=pdf_converter,
            )
        )
        client.post("/md-to-pdf", json={"pointers": [GITLAB_POINTER]})
        pdf_converter.convert.assert_called_once_with("The summary.")


if __name__ == "__main__":
    unittest.main()
