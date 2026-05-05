"""Tests for API route authorization scope wiring."""

from __future__ import annotations

from typing import Any
from unittest import TestCase, mock

from fastapi.testclient import TestClient

from dmis_api.api import API


class MockAiohttpResponse:
    def raise_for_status(self) -> None:
        return None

    async def json(self) -> dict[str, Any]:
        return {"ok": True}


class MockAiohttpContext:
    async def __aenter__(self) -> MockAiohttpResponse:
        return MockAiohttpResponse()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class MockAiohttpClient:
    def __init__(self) -> None:
        self.get = mock.Mock(return_value=MockAiohttpContext())
        self.post = mock.Mock(return_value=MockAiohttpContext())

    async def close(self) -> None:
        return None


class TestAPIAuthorizationRoutes(TestCase):
    """Tests for route-specific scope authorization."""

    def setUp(self) -> None:
        scope_by_env = {
            "DMISAPI_SEARCHENG_SCOPE": "test.search",
            "DMISAPI_STOCHAN_SCOPE": "test.query",
            "DMISAPI_CONGATEWAY_SCOPE": "test.connector",
        }
        self.read_env_variable_patcher = mock.patch("dmis_api.api.read_env_variable")
        mock_read_env_variable = self.read_env_variable_patcher.start()
        self.addCleanup(self.read_env_variable_patcher.stop)
        mock_read_env_variable.side_effect = lambda name, required=False: scope_by_env.get(name)

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
            log_level="debug",
        )
        self.api.create_http_client = mock.Mock(return_value=MockAiohttpClient())

    def test_search_engine_get_requires_search_scope(self) -> None:
        with TestClient(self.api.app) as client:
            response = client.get(
                "/search_engine/test",
                headers={"Authorization": "Bearer token"},
            )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.search"],
        )

    def test_search_engine_post_requires_search_scope(self) -> None:
        with TestClient(self.api.app) as client:
            response = client.post(
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
        with TestClient(self.api.app) as client:
            response = client.get(
                "/stochastic-analyzer/test",
                headers={"Authorization": "Bearer token"},
            )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.query"],
        )

    def test_stochastic_post_requires_query_scope(self) -> None:
        with TestClient(self.api.app) as client:
            response = client.post(
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
        with TestClient(self.api.app) as client:
            response = client.get(
                "/connector/test",
                headers={"Authorization": "Bearer token"},
            )

        assert response.status_code == 200
        self.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer token",
            required_scopes=["test.connector"],
        )

    def test_connector_post_requires_connector_scope(self) -> None:
        with TestClient(self.api.app) as client:
            response = client.post(
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
        with TestClient(self.api.app) as client:
            client.get(
                "/search_engine/test",
                headers={"Authorization": "Bearer token"},
            )

        assert self.api.http_client is not None
        self.api.http_client.get.assert_called_once_with(
            "http://search-engine.test/test",
            params={},
            headers={"Authorization": "Bearer token"},
        )
