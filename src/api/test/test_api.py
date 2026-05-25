"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from unittest import TestCase, mock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from dmis_api.api import API


class Response:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def raise_for_status(self):
        return None

    async def json(self):
        return {"ok": True}


class HttpClient:
    def __init__(self):
        self.calls = []
        self.closed = False

    def get(self, url, *, params=None, headers=None):
        self.calls.append(("GET", url, params, headers))
        return Response()

    def post(self, url, *, params=None, json=None, headers=None):
        self.calls.append(("POST", url, params, json, headers))
        return Response()

    async def close(self):
        self.closed = True


class TestAPI(TestCase):
    SCOPES = {
        "DMISAPI_SEARCHENG_SCOPE": "search:access",
        "DMISAPI_STOCHAN_SCOPE": "stochan:access",
        "DMISAPI_CONGATEWAY_SCOPE": "connector:access",
    }

    URLS = {
        "searcheng": "http://search.test",
        "stochan": "http://stochan.test",
        "congateway": "http://connector.test",
    }

    CLAIMS = {
        "sub": "user-1",
        "preferred_username": "tester",
        "azp": "frontend",
    }

    def setUp(self):
        self.env_patch = mock.patch(
            "dmis_api.api.read_env_variable",
            side_effect=lambda name, required=True: self.SCOPES.get(name),
        )
        self.token_patch = mock.patch("dmis_api.api.TokenVerifier")
        self.auth_patch = mock.patch("dmis_api.api.AuthRoutes")
        self.info_patch = mock.patch("dmis_api.api.dms_info")
        self.warning_patch = mock.patch("dmis_api.api.dms_warning")

        self.token_class = self.token_patch.start()
        self.auth_class = self.auth_patch.start()
        self.env_patch.start()
        self.info_patch.start()
        self.warning_patch.start()

        self.addCleanup(self.token_patch.stop)
        self.addCleanup(self.auth_patch.stop)
        self.addCleanup(self.env_patch.stop)
        self.addCleanup(self.info_patch.stop)
        self.addCleanup(self.warning_patch.stop)

    def make_api(self):
        verifier = mock.Mock()
        verifier.verify_access_token.return_value = self.CLAIMS
        self.token_class.return_value = verifier

        auth_routes = mock.Mock()
        auth_routes.close_session = mock.AsyncMock()
        auth_routes.code_exchange = mock.AsyncMock()
        auth_routes.check_auth = mock.AsyncMock()
        auth_routes.auth_me = mock.AsyncMock()
        auth_routes.refresh_auth = mock.AsyncMock()
        auth_routes.logout_auth = mock.AsyncMock()
        self.auth_class.return_value = auth_routes

        api = API(upstream_urls=self.URLS)

        http_client = HttpClient()
        api.create_http_client = mock.Mock(return_value=http_client)

        return api, http_client

    def test_invalid_or_missing_token_blocks_proxying(self):
        for token in [None, "123456789"]:
            with self.subTest(token=token):
                api, http_client = self.make_api()
                api.token_verifier.verify_access_token.side_effect = HTTPException(status_code=401)

                with TestClient(api.app) as client:
                    if token:
                        client.cookies.set("access_token", token)
                    response = client.get("/search_engine/documents")

                assert response.status_code == 401
                assert http_client.calls == []

    def test_scopes_are_optional(self):
        self.env_patch.stop()
        self.env_patch = mock.patch("dmis_api.api.read_env_variable", return_value=None)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        api, _ = self.make_api()

        assert api.required_scopes == {
            "searcheng": [],
            "stochan": [],
            "congateway": [],
        }

    def test_lifespan_closes_sessions(self):
        api, http_client = self.make_api()

        with TestClient(api.app):
            assert api.http_client is http_client

        assert http_client.closed is True
        api.auth_routes.close_session.assert_awaited_once()
