"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Route-level tests — ``ConfluenceInterfacer`` is mocked (no Live env or Confluence hosts).
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from confluence_service.collector_api import API


class TestCollectorAuthUserAndDefinedFields(unittest.TestCase):
    """Covers `/auth_user` contract and `/defined_fields` union keys."""

    def setUp(self) -> None:
        mock_inst = MagicMock()
        mock_inst.session = MagicMock()
        mock_inst.session.aclose = AsyncMock(return_value=None)
        mock_inst.defined_fields = {
            "content": None,
            "name": None,
            "unique_pointer": None,
        }

        self._ci = patch("confluence_service.collector_api.ConfluenceInterfacer", return_value=mock_inst)
        self._ci.start()
        self.mock_inst = mock_inst

    def tearDown(self) -> None:
        self._ci.stop()

    def test_auth_user_returns_gateway_contract(self) -> None:
        api = API()
        with TestClient(api.app) as client:
            res = client.get("/auth_user")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body.get("schema_version"), 1)
        self.assertEqual(body.get("connector"), "confluence")
        self.assertEqual(body.get("flow"), "request_headers_credentials")
        self.assertIn("required_headers", body)
        self.assertIn("oauth", body)
        self.assertIn("documentation_url", body["oauth"])
        self.assertEqual(body.get("type"), "api_token")
        self.assertEqual(body.get("method"), "manual")
        names = {h["name"] for h in body["required_headers"]}
        self.assertEqual(names, {"X-Confluence-Email", "X-Confluence-Token"})

    def test_defined_fields_returns_sorted_keys_from_interfacer(self) -> None:
        api = API()
        with TestClient(api.app) as client:
            res = client.get("/defined_fields")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), ["content", "name", "unique_pointer"])

    def test_get_files_without_headers_returns_empty_list(self) -> None:
        api = API()
        with TestClient(api.app) as client:
            res = client.post("/get_files", json={"file_pointers": ["ignored"]})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])
