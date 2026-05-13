"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the gateway API routes.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway.schemas import (
    InputItem,
    MetadataTemplate,
)
from gateway.routes import create_router

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


def _make_client(
    pdf_converter=None,
    connector=None,
    summarizer=None,
) -> TestClient:
    """Wire up a FastAPI app with the given services and return a test client."""
    pdf_converter = pdf_converter or MagicMock()
    connector = connector or AsyncMock()
    summarizer = summarizer or AsyncMock()

    app = FastAPI()
    app.include_router(create_router(pdf_converter, connector, summarizer))
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /md-to-pdf
# ---------------------------------------------------------------------------


class TestMdToPdfEndpoint(unittest.TestCase):
    def _make_pdf_client(self, pdf_converter=None) -> TestClient:
        pdf_converter = pdf_converter or MagicMock()
        pdf_converter.convert.return_value = b"%PDF-fake-bytes"
        return _make_client(pdf_converter=pdf_converter)

    def test_returns_pdf_content_type(self) -> None:
        client = self._make_pdf_client()
        resp = client.post("/md-to-pdf", json={"markdown": "Summary text."})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/pdf", resp.headers["content-type"])

    def test_returns_pdf_bytes(self) -> None:
        client = self._make_pdf_client()
        resp = client.post("/md-to-pdf", json={"markdown": "Summary text."})
        self.assertEqual(resp.content, b"%PDF-fake-bytes")

    def test_returns_500_when_converter_fails(self) -> None:
        pdf_converter = MagicMock()
        pdf_converter.convert.side_effect = Exception("converter error")
        client = _make_client(pdf_converter=pdf_converter)
        resp = client.post("/md-to-pdf", json={"markdown": "Summary text."})
        self.assertEqual(resp.status_code, 500)

    def test_pdf_converter_called_with_markdown_text(self) -> None:
        pdf_converter = MagicMock()
        pdf_converter.convert.return_value = b"%PDF"
        client = _make_client(pdf_converter=pdf_converter)
        client.post("/md-to-pdf", json={"markdown": "The summary."})
        pdf_converter.convert.assert_called_once_with("The summary.")


# ---------------------------------------------------------------------------
# POST /summarize
# ---------------------------------------------------------------------------


class TestSummarizeEndpoint(unittest.TestCase):

    def test_returns_200_with_summary(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = {"summary": "A nice summary."}

        client = _make_client(connector=connector, summarizer=summarizer)
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "A nice summary.")

    def test_returns_empty_summary_when_connector_returns_nothing(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = []

        client = _make_client(connector=connector)
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER]})

        self.assertEqual(resp.status_code, 200)
        self.assertIn("summary", resp.json())
        self.assertNotEqual(resp.json()["summary"], "")

    def test_returns_empty_summary_when_connector_raises(self) -> None:
        from aiohttp import ClientError

        connector = AsyncMock()
        connector.get_file_contents.side_effect = ClientError("unreachable")

        client = _make_client(connector=connector)
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "")

    def test_returns_empty_summary_when_summarizer_returns_none(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = None

        client = _make_client(connector=connector, summarizer=summarizer)
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "")

    def test_multiple_pointers_all_fetched(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [
            _make_item(),
            _make_item(pointer=GITLAB_POINTER_2),
        ]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = {"summary": "Combined summary."}

        client = _make_client(connector=connector, summarizer=summarizer)
        resp = client.post("/summarize", json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]})

        self.assertEqual(resp.status_code, 200)
        connector.get_file_contents.assert_called_once_with([GITLAB_POINTER, GITLAB_POINTER_2], None)

    def test_authorization_header_forwarded_to_connector(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [_make_item()]

        summarizer = AsyncMock()
        summarizer.summarize.return_value = {"summary": "ok"}

        client = _make_client(connector=connector, summarizer=summarizer)
        client.post(
            "/summarize",
            json={"pointers": [GITLAB_POINTER]},
            headers={"Authorization": "Bearer token123"},
        )

        connector.get_file_contents.assert_called_once_with([GITLAB_POINTER], "Bearer token123")

    def test_empty_pointers_returns_empty_summary(self) -> None:
        client = _make_client()
        resp = client.post("/summarize", json={"pointers": []})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "")


# ---------------------------------------------------------------------------
# POST /merge
# ---------------------------------------------------------------------------


class TestMergeEndpoint(unittest.TestCase):

    def test_returns_200_with_merged_result(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [
            _make_item(),
            _make_item(pointer=GITLAB_POINTER_2),
        ]

        summarizer = AsyncMock()
        summarizer.merge.return_value = {"summary": "Merged content."}

        client = _make_client(connector=connector, summarizer=summarizer)
        resp = client.post("/merge", json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "Merged content.")

    def test_returns_empty_summary_for_single_pointer(self) -> None:
        client = _make_client()
        resp = client.post("/merge", json={"pointers": [GITLAB_POINTER]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "")

    def test_returns_empty_summary_for_no_pointers(self) -> None:
        client = _make_client()
        resp = client.post("/merge", json={"pointers": []})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "")

    def test_returns_empty_summary_when_connector_raises(self) -> None:
        from aiohttp import ClientError

        connector = AsyncMock()
        connector.get_file_contents.side_effect = ClientError("unreachable")

        client = _make_client(connector=connector)
        resp = client.post("/merge", json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "")

    def test_returns_empty_summary_when_connector_returns_nothing(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = []

        client = _make_client(connector=connector)
        resp = client.post("/merge", json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]})

        self.assertEqual(resp.status_code, 200)
        self.assertIn("summary", resp.json())
        self.assertNotEqual(resp.json()["summary"], "")

    def test_returns_empty_summary_when_merge_returns_none(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [
            _make_item(),
            _make_item(pointer=GITLAB_POINTER_2),
        ]

        summarizer = AsyncMock()
        summarizer.merge.return_value = None

        client = _make_client(connector=connector, summarizer=summarizer)
        resp = client.post("/merge", json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"], "")

    def test_authorization_header_forwarded_to_connector(self) -> None:
        connector = AsyncMock()
        connector.get_file_contents.return_value = [
            _make_item(),
            _make_item(pointer=GITLAB_POINTER_2),
        ]

        summarizer = AsyncMock()
        summarizer.merge.return_value = {"summary": "ok"}

        client = _make_client(connector=connector, summarizer=summarizer)
        client.post(
            "/merge",
            json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]},
            headers={"Authorization": "Bearer token123"},
        )

        connector.get_file_contents.assert_called_once_with([GITLAB_POINTER, GITLAB_POINTER_2], "Bearer token123")

    def test_merge_called_with_fetched_items(self) -> None:
        items = [_make_item(), _make_item(pointer=GITLAB_POINTER_2)]

        connector = AsyncMock()
        connector.get_file_contents.return_value = items

        summarizer = AsyncMock()
        summarizer.merge.return_value = {"summary": "done"}

        client = _make_client(connector=connector, summarizer=summarizer)
        client.post("/merge", json={"pointers": [GITLAB_POINTER, GITLAB_POINTER_2]})

        summarizer.merge.assert_called_once_with(items)
