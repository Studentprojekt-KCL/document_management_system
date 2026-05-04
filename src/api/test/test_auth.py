"""Tests for OAuth2/OIDC bearer token verification."""

from __future__ import annotations

from typing import Any
from unittest import TestCase, mock

import jwt
from fastapi import HTTPException

from dmis_api.auth import TokenVerifier


class TestTokenVerifier(TestCase):
    """Tests for TokenVerifier."""

    def setUp(self) -> None:
        self.verifier = TokenVerifier(
            issuer="https://issuer.example.com/realms/test",
            jwks_url="https://issuer.example.com/realms/test/protocol/openid-connect/certs",
            expected_audience=["test-api"],
            allowed_azp=["test-frontend"],
        )

    @staticmethod
    def signing_key() -> mock.Mock:
        key = mock.Mock()
        key.key = "public-key"
        return key

    @staticmethod
    def assert_www_authenticate(exc: HTTPException, expected: str) -> None:
        assert exc.headers is not None
        assert "WWW-Authenticate" in exc.headers
        assert expected in exc.headers["WWW-Authenticate"]

    def test_missing_authorization_header_returns_401(self) -> None:
        with self.assertRaises(HTTPException) as exc_info:
            self.verifier.verify_access_token(None)

        assert exc_info.exception.status_code == 401
        assert exc_info.exception.headers == {"WWW-Authenticate": "Bearer"}

    def test_wrong_authorization_scheme_returns_400(self) -> None:
        with self.assertRaises(HTTPException) as exc_info:
            self.verifier.verify_access_token("Basic abc123")

        assert exc_info.exception.status_code == 400
        self.assert_www_authenticate(exc_info.exception, 'error="invalid_request"')

    def test_missing_bearer_token_returns_400(self) -> None:
        with self.assertRaises(HTTPException) as exc_info:
            self.verifier.verify_access_token("Bearer")

        assert exc_info.exception.status_code == 400
        self.assert_www_authenticate(exc_info.exception, 'error="invalid_request"')

    @mock.patch("dmis_api.auth.jwt.decode")
    @mock.patch("dmis_api.auth.PyJWKClient.get_signing_key_from_jwt")
    def test_invalid_token_returns_401(
        self,
        mock_get_signing_key_from_jwt: mock.Mock,
        mock_decode: mock.Mock,
    ) -> None:
        mock_get_signing_key_from_jwt.return_value = self.signing_key()
        mock_decode.side_effect = jwt.InvalidTokenError("bad token")

        with self.assertRaises(HTTPException) as exc_info:
            self.verifier.verify_access_token("Bearer bad.token")

        assert exc_info.exception.status_code == 401
        self.assert_www_authenticate(exc_info.exception, 'error="invalid_token"')

    @mock.patch("dmis_api.auth.jwt.decode")
    @mock.patch("dmis_api.auth.PyJWKClient.get_signing_key_from_jwt")
    def test_decode_uses_expected_issuer_audience_and_algorithm(
        self,
        mock_get_signing_key_from_jwt: mock.Mock,
        mock_decode: mock.Mock,
    ) -> None:
        mock_get_signing_key_from_jwt.return_value = self.signing_key()
        mock_decode.return_value = {
            "sub": "user-1",
            "azp": "test-frontend",
            "scope": "openid test.search",
        }

        self.verifier.verify_access_token("Bearer valid.token")

        _, kwargs = mock_decode.call_args

        assert kwargs["algorithms"] == ["RS256"]
        assert kwargs["issuer"] == "https://issuer.example.com/realms/test"
        assert kwargs["audience"] == ["test-api"]
        assert kwargs["options"] == {"verify_aud": True}

    @mock.patch("dmis_api.auth.jwt.decode")
    @mock.patch("dmis_api.auth.PyJWKClient.get_signing_key_from_jwt")
    def test_wrong_azp_returns_403(
        self,
        mock_get_signing_key_from_jwt: mock.Mock,
        mock_decode: mock.Mock,
    ) -> None:
        mock_get_signing_key_from_jwt.return_value = self.signing_key()
        mock_decode.return_value = {
            "sub": "user-1",
            "azp": "wrong-client",
            "scope": "openid test.search",
        }

        with self.assertRaises(HTTPException) as exc_info:
            self.verifier.verify_access_token("Bearer valid.token")

        assert exc_info.exception.status_code == 403
        self.assert_www_authenticate(exc_info.exception, 'error="insufficient_scope"')

    @mock.patch("dmis_api.auth.jwt.decode")
    @mock.patch("dmis_api.auth.PyJWKClient.get_signing_key_from_jwt")
    def test_missing_required_scope_returns_403(
        self,
        mock_get_signing_key_from_jwt: mock.Mock,
        mock_decode: mock.Mock,
    ) -> None:
        mock_get_signing_key_from_jwt.return_value = self.signing_key()
        mock_decode.return_value = {
            "sub": "user-1",
            "azp": "test-frontend",
            "scope": "openid profile",
        }

        with self.assertRaises(HTTPException) as exc_info:
            self.verifier.verify_access_token(
                "Bearer valid.token",
                required_scopes=["test.search"],
            )

        assert exc_info.exception.status_code == 403
        self.assert_www_authenticate(exc_info.exception, 'error="insufficient_scope"')
        self.assert_www_authenticate(exc_info.exception, 'scope="test.search"')

    @mock.patch("dmis_api.auth.jwt.decode")
    @mock.patch("dmis_api.auth.PyJWKClient.get_signing_key_from_jwt")
    def test_valid_token_with_required_scope_returns_claims(
        self,
        mock_get_signing_key_from_jwt: mock.Mock,
        mock_decode: mock.Mock,
    ) -> None:
        mock_get_signing_key_from_jwt.return_value = self.signing_key()

        claims: dict[str, Any] = {
            "sub": "user-1",
            "preferred_username": "admin",
            "azp": "test-frontend",
            "aud": ["test-api"],
            "scope": "openid profile test.search",
        }
        mock_decode.return_value = claims

        result = self.verifier.verify_access_token(
            "Bearer valid.token",
            required_scopes=["test.search"],
        )

        assert result == claims