"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

import json
from unittest import IsolatedAsyncioTestCase, mock

from fastapi import HTTPException, Request

from dmis_api.auth_routes import AuthRoutes


class Response:
    def __init__(self, status=200, payload=None):
        self.status = status
        self.payload = payload or {}

    async def json(self):
        return self.payload


class HttpClient:
    def __init__(self, response):
        self.response = response
        self.closed = False

    async def post(self, *_args, **_kwargs):
        return self.response

    def close(self):
        self.closed = True


class TestAuthRoutes(IsolatedAsyncioTestCase):
    ENV = {
        "DMISAPI_AD_TOKEN_URL": "https://identity-provider.test/token",
        "DMISAPI_AD_LOGOUT_URL": "https://identity-provider.test/logout",
        "DMISAPI_AD_CLIENT_ID": "dmis-api",
        "DMISAPI_ADMIN_ROLES": "admin, owner",
    }

    CLAIMS = {
        "preferred_username": "tester",
        "email": "tester@example.test",
        "resource_access": {
            "dmis-api": {
                "roles": ["user", "admin"],
            },
        },
        "realm_access": {
            "roles": ["realm-user"],
        },
    }

    TOKENS = {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "id_token": "id-token",
    }

    def setUp(self):
        self.env_patch = mock.patch(
            "dmis_api.auth_routes.read_env_variable",
            side_effect=lambda name, required=True: self.ENV.get(name),
        )
        self.warning_patch = mock.patch("dmis_api.auth_routes.dms_warning")

        self.env_patch.start()
        self.warning_patch.start()

        self.addCleanup(self.env_patch.stop)
        self.addCleanup(self.warning_patch.stop)

    def make_routes(self, claims=None, token_response=None):
        verifier = mock.Mock()
        verifier.verify_access_token.return_value = self.CLAIMS if claims is None else claims

        routes = AuthRoutes(verifier)

        if token_response is not None:
            routes._session = HttpClient(token_response)

        return routes, verifier

    @staticmethod
    def make_request(origin="https://frontend.test"):
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/",
                "headers": [(b"origin", origin.encode())],
            }
        )

    async def test_check_auth_requires_authenticated_user(self):
        routes, verifier = self.make_routes()
        verifier.verify_access_token.return_value = None

        with self.assertRaises(HTTPException) as raised:
            await routes.check_auth("access-token")

        assert raised.exception.status_code == 401

    async def test_check_auth_requires_client_role(self):
        routes, _ = self.make_routes(
            claims={
                **self.CLAIMS,
                "resource_access": {
                    "dmis-api": {
                        "roles": [],
                    },
                },
            }
        )

        with self.assertRaises(HTTPException) as raised:
            await routes.check_auth("access-token")

        assert raised.exception.status_code == 403

    async def test_check_auth_returns_authenticated_user(self):
        routes, _ = self.make_routes()

        response = await routes.check_auth("access-token")
        payload = json.loads(response.body)

        assert response.status_code == 200
        assert payload == {
            "authenticated": True,
            "user": {
                "username": "tester",
            },
        }

    async def test_auth_me_requires_authenticated_user(self):
        routes, verifier = self.make_routes()
        verifier.verify_access_token.return_value = None

        with self.assertRaises(HTTPException) as raised:
            await routes.auth_me("access-token")

        assert raised.exception.status_code == 401

    async def test_auth_me_returns_user_identity_and_roles(self):
        routes, _ = self.make_routes()

        response = await routes.auth_me("access-token")
        payload = json.loads(response.body)

        assert response.status_code == 200
        assert payload == {
            "authenticated": True,
            "user": {
                "username": "tester",
                "email": "tester@example.test",
                "client_roles": ["user", "admin"],
                "realm_roles": ["realm-user"],
            },
        }

    async def test_check_admin_requires_authenticated_user(self):
        routes, verifier = self.make_routes()
        verifier.verify_access_token.return_value = None

        with self.assertRaises(HTTPException) as raised:
            await routes.check_admin("access-token")

        assert raised.exception.status_code == 401

    async def test_check_admin_returns_true_for_configured_admin_role(self):
        routes, _ = self.make_routes()

        response = await routes.check_admin("access-token")
        payload = json.loads(response.body)

        assert response.status_code == 200
        assert payload == {"admin": True}

    async def test_check_admin_returns_false_without_configured_admin_role(self):
        routes, _ = self.make_routes(
            claims={
                **self.CLAIMS,
                "resource_access": {
                    "dmis-api": {
                        "roles": ["user"],
                    },
                },
            }
        )

        response = await routes.check_admin("access-token")
        payload = json.loads(response.body)

        assert response.status_code == 200
        assert payload == {"admin": False}

    async def test_code_exchange_returns_success_when_provider_returns_tokens(self):
        routes, _ = self.make_routes(token_response=Response(payload=self.TOKENS))

        response = await routes.code_exchange(
            self.make_request(),
            code="auth-code",
            code_verifier="verifier",
        )
        payload = json.loads(response.body)

        assert response.status_code == 200
        assert payload == {"message": "Login successful"}

    async def test_code_exchange_raises_bad_gateway_when_provider_exchange_fails(self):
        routes, _ = self.make_routes(token_response=Response(status=500, payload={"error": "server_error"}))

        with self.assertRaises(HTTPException) as raised:
            await routes.code_exchange(
                self.make_request(),
                code="auth-code",
                code_verifier="verifier",
            )

        assert raised.exception.status_code == 502

    async def test_refresh_requires_refresh_token(self):
        routes, _ = self.make_routes()

        response = await routes.refresh_auth(None)
        payload = json.loads(response.body)

        assert response.status_code == 401
        assert payload == {"message": "Missing refresh token"}

    async def test_refresh_returns_success_when_provider_returns_tokens(self):
        routes, _ = self.make_routes(token_response=Response(payload=self.TOKENS))

        response = await routes.refresh_auth("refresh-token")
        payload = json.loads(response.body)

        assert response.status_code == 200
        assert payload == {"message": "Session refreshed"}

    async def test_refresh_raises_bad_gateway_when_provider_exchange_fails(self):
        routes, _ = self.make_routes(token_response=Response(status=500, payload={"error": "server_error"}))

        with self.assertRaises(HTTPException) as raised:
            await routes.refresh_auth("refresh-token")

        assert raised.exception.status_code == 502

    async def test_logout_returns_provider_logout_url(self):
        routes, _ = self.make_routes()

        response = await routes.logout_auth(self.make_request(), id_token="id-token")
        payload = json.loads(response.body)

        assert response.status_code == 200
        assert payload == {
            "logout_url": "https://identity-provider.test/logout?"
            "post_logout_redirect_uri=https%3A%2F%2Ffrontend.test%2F&client_id=dmis-api&id_token_hint=id-token"
        }

    async def test_close_session_closes_created_http_session(self):
        routes, _ = self.make_routes(token_response=Response(payload=self.TOKENS))

        await routes.close_session()

        assert routes._session.closed is True
