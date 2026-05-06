"""Tests for api.py as a thin authenticated proxy."""

from __future__ import annotations

from typing import Any
from unittest import TestCase, mock

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from dmis_api.api import API


class FakeResponse:
    """Minimal aiohttp-like response object."""

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> dict[str, bool]:
        return {"ok": True}


class FakeHttpClient:
    """Fake HTTP client that records outgoing proxy requests."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.closed = False

    def get(self, url: str, *, params: dict[str, str] | None = None, headers: dict[str, str] | None = None,) -> FakeResponse:
        self.calls.append(("GET", url, params, headers))
        return FakeResponse()

    def post(self, url: str, *, params: dict[str, str] | None = None, json: dict[str, Any] | None = None, headers: dict[str, str] | None = None,) -> FakeResponse:
        self.calls.append(("POST", url, params, json, headers))
        return FakeResponse()

    async def close(self) -> None:
        self.closed = True


class FakeAuthRoutes:
    """Minimal fake for AuthRoutes so api.py can register auth routes."""

    def __init__(self, *_: object, **__: object) -> None:
        self.close_session = mock.AsyncMock()

    async def code_exchange(self) -> JSONResponse:
        return JSONResponse({})

    async def check_auth(self) -> JSONResponse:
        return JSONResponse({})

    async def auth_me(self) -> JSONResponse:
        return JSONResponse({})

    async def refresh_auth(self) -> JSONResponse:
        return JSONResponse({})

    async def logout_auth(self) -> JSONResponse:
        return JSONResponse({})


class TestAPI(TestCase):
    """tests for api.py."""

    def setUp(self) -> None:
        scopes = {
            "DMISAPI_SEARCHENG_SCOPE": "search:access",
            "DMISAPI_STOCHAN_SCOPE": "stochan:access",
            "DMISAPI_CONGATEWAY_SCOPE": "connector:access",
        }

        self.env_patch = mock.patch(
            "dmis_api.api.read_env_variable",
            side_effect=lambda name, required=True: scopes.get(name),
        )
        self.token_verifier_patch = mock.patch("dmis_api.api.TokenVerifier")
        self.auth_routes_patch = mock.patch("dmis_api.api.AuthRoutes", FakeAuthRoutes)
        self.info_patch = mock.patch("dmis_api.api.dms_info")
        self.warning_patch = mock.patch("dmis_api.api.dms_warning")

        self.mock_token_verifier_class = self.token_verifier_patch.start()
        self.env_patch.start()
        self.auth_routes_patch.start()
        self.info_patch.start()
        self.warning_patch.start()

        self.addCleanup(self.token_verifier_patch.stop)
        self.addCleanup(self.env_patch.stop)
        self.addCleanup(self.auth_routes_patch.stop)
        self.addCleanup(self.info_patch.stop)
        self.addCleanup(self.warning_patch.stop)

    def make_api(self) -> tuple[API, FakeHttpClient]:
        token_verifier = mock.Mock()
        token_verifier.verify_access_token.return_value = {
            "sub": "user-1",
            "preferred_username": "tester",
            "azp": "frontend",
        }
        self.mock_token_verifier_class.return_value = token_verifier

        api = API(
            upstream_urls={
                "searcheng": "http://search.test",
                "stochan": "http://stochan.test",
                "congateway": "http://connector.test",
            }
        )

        fake_client = FakeHttpClient()
        api.create_http_client = mock.Mock(return_value=fake_client)

        return api, fake_client

    def test_valid_access_token_cookie_allows_get_proxying(self) -> None:
        api, fake_client = self.make_api()

        with TestClient(api.app) as client:
            client.cookies.set("access_token", "valid-token")
            response = client.get(
                "/search_engine/documents",
                params={"q": "law"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        api.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer valid-token",
            required_scopes=["search:access"],
        )

        assert fake_client.calls == [
            (
                "GET",
                "http://search.test/documents",
                {"q": "law"},
                {"Authorization": "Bearer valid-token"},
            )
        ]

    def test_valid_access_token_cookie_allows_post_proxying(self) -> None:
        api, fake_client = self.make_api()

        with TestClient(api.app) as client:
            client.cookies.set("access_token", "valid-token")
            response = client.post(
                "/connector/import",
                params={"source": "x"},
                json={"document": "hello"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        api.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer valid-token",
            required_scopes=["connector:access"],
        )

        assert fake_client.calls == [
            (
                "POST",
                "http://connector.test/import",
                {"source": "x"},
                {"document": "hello"},
                {"Authorization": "Bearer valid-token"},
            )
        ]

    def test_missing_access_token_cookie_blocks_proxying(self) -> None:
        api, fake_client = self.make_api()
        api.token_verifier.verify_access_token.side_effect = HTTPException(status_code=401)

        with TestClient(api.app) as client:
            response = client.get("/search_engine/documents")

        assert response.status_code == 401
        assert fake_client.calls == []

        api.token_verifier.verify_access_token.assert_called_once_with(
            None,
            required_scopes=["search:access"],
        )

    def test_invalid_access_token_cookie_blocks_proxying(self) -> None:
        api, fake_client = self.make_api()
        api.token_verifier.verify_access_token.side_effect = HTTPException(status_code=401)

        with TestClient(api.app) as client:
            client.cookies.set("access_token", "123456789")
            response = client.get("/search_engine/documents")

        assert response.status_code == 401
        assert fake_client.calls == []

        api.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer 123456789",
            required_scopes=["search:access"],
        )

    def test_localhost_referer_does_not_bypass_token_validation(self) -> None:
        """With the current implementation this should fail, which is expected since we have a localhost bypass"""
        api, _ = self.make_api()
        api.token_verifier.verify_access_token.side_effect = HTTPException(status_code=401)

        with self.assertRaises(HTTPException):
            api.authorize(
                authorization="Bearer 123456789",
                host="http://localhost:3000",
                required_scopes=["search:access"],
            )

        api.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer 123456789",
            required_scopes=["search:access"],
        )

    def test_scope_configuration_is_optional_for_proxy_routes(self) -> None:
        self.env_patch.stop()
        self.env_patch = mock.patch("dmis_api.api.read_env_variable", return_value=None)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        api, fake_client = self.make_api()

        with TestClient(api.app) as client:
            client.cookies.set("access_token", "valid-token")
            response = client.get("/search_engine/documents")

        assert response.status_code == 200

        api.token_verifier.verify_access_token.assert_called_once_with(
            "Bearer valid-token",
            required_scopes=[],
        )

        assert fake_client.calls == [
            (
                "GET",
                "http://search.test/documents",
                {},
                {"Authorization": "Bearer valid-token"},
            )
        ]

    def test_lifespan_creates_and_closes_proxy_sessions(self) -> None:
        api, fake_client = self.make_api()

        assert api.http_client is None
        assert fake_client.closed is False

        with TestClient(api.app):
            assert api.http_client is fake_client
            assert fake_client.closed is False

        assert fake_client.closed is True
        api.auth_routes.close_session.assert_awaited_once()