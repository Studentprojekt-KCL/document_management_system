"""Tests for API route authorization scope wiring."""

from __future__ import annotations

from unittest import TestCase, mock
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from dmis_api.api import API


class TestAPIAuthorizationRoutes(TestCase):
    """Tests for route-specific scope authorization."""

    def setUp(self) -> None:
        self.token_verifier = mock.Mock()
        self.token_verifier.verify_access_token.return_value = {
            "sub": "user-1",
            "preferred_username": "admin",
            "azp": "test-frontend",
        }

        self.api = API(
            upstream_urls={
                "searcheng": "http://search-engine.test",
                "stochan": "http://stochan.test",
                "congateway": "http://connector.test",
            },
            token_verifier=self.token_verifier,
            required_scopes={
                "searcheng": ["test.search"],
                "stochan": ["test.query"],
                "congateway": ["test.connector"],
            },
            log_level="debug",
        )

        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        self.api.http_client.get = AsyncMock(return_value=response)
        self.api.http_client.post = AsyncMock(return_value=response)
        self.client = TestClient(self.api.app)

    def test_search_engine_get_requires_search_scope(self) -> None:
        response = self.client.get(
            "/search_engine/test",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.search"],
        )

    def test_search_engine_post_requires_search_scope(self) -> None:
        response = self.client.post(
            "/search_engine/test",
            headers={"Authorization": "Bearer token"},
            json={"query": "hello"},
        )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.search"],
        )

    def test_stochastic_get_requires_query_scope(self) -> None:
        response = self.client.get(
            "/stochastic-analyzer/test",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.query"],
        )

    def test_stochastic_post_requires_query_scope(self) -> None:
        response = self.client.post(
            "/stochastic-analyzer/test",
            headers={"Authorization": "Bearer token"},
            json={"pointers": ["abc"]},
        )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.query"],
        )

    def test_connector_get_requires_connector_scope(self) -> None:
        response = self.client.get(
            "/connector/test",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.connector"],
        )

    def test_connector_post_requires_connector_scope(self) -> None:
        response = self.client.post(
            "/connector/test",
            headers={"Authorization": "Bearer token"},
            json={"data": "hello"},
        )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.connector"],
        )

    def test_search_engine_get_forwards_authorization_header(self) -> None:
        self.client.get(
            "/search_engine/test",
            headers={"Authorization": "Bearer token"},
        )

        self.api.http_client.get.assert_awaited_once_with(
            "http://search-engine.test/test",
            params={},
            headers={"Authorization": "Bearer token"},
        )