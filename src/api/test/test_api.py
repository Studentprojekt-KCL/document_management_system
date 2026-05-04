"""Tests for API startup, routes, and authorization."""

from __future__ import annotations

from typing import Any
from unittest import TestCase, mock

from fastapi import HTTPException
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


class TestAPI(TestCase):
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
            log_level="debug",
        )

        self.api.create_http_client = mock.Mock(return_value=MockAiohttpClient())

    def test_search_engine_get_route_works(self) -> None:
        with TestClient(self.api.app) as client:
            response = client.get(
                "/search_engine/test",
                headers={"Authorization": "Bearer token"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_search_engine_post_route_works(self) -> None:
        with TestClient(self.api.app) as client:
            response = client.post(
                "/search_engine/test",
                headers={"Authorization": "Bearer token"},
                json={"query": "hello"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_stochastic_analyzer_route_works(self) -> None:
        with TestClient(self.api.app) as client:
            response = client.get(
                "/stochastic-analyzer/test",
                headers={"Authorization": "Bearer token"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_connector_route_works(self) -> None:
        with TestClient(self.api.app) as client:
            response = client.get(
                "/connector/test",
                headers={"Authorization": "Bearer token"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_authorization_is_required(self) -> None:
        self.token_verifier.verify_access_token.side_effect = HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

        with TestClient(self.api.app) as client:
            response = client.get("/search_engine/test")

        assert response.status_code == 401