"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from unittest import TestCase, mock

import jwt
from fastapi import HTTPException

from dmis_api.auth import TokenVerifier


class TestTokenVerifier(TestCase):
    """Unittests for the TokenVerifier class."""

    ENV = {
        "DMISAPI_AD_URL": "https://identity-provider.test/tenant",
        "DMISAPI_AD_JWKS_URL": "https://identity-provider.test/tenant/.well-known/jwks.json",
        "DMISAPI_AD_AUDIENCE": "dmis-api",
        "DMISAPI_AD_ALLOWED_AZP": "stakeholder-frontend,internal-frontend",
    }

    CLAIMS = {
        "sub": "user-1",
        "preferred_username": "tester",
        "azp": "stakeholder-frontend",
        "scope": "search:access connector:access",
    }

    def setUp(self):
        self.env_patch = mock.patch(
            "dmis_api.auth.read_env_variable",
            side_effect=lambda name, required=True: self.ENV.get(name),
        )
        self.jwks_patch = mock.patch("dmis_api.auth.PyJWKClient")
        self.decode_patch = mock.patch("dmis_api.auth.jwt.decode")
        self.info_patch = mock.patch("dmis_api.auth.dms_info")

        self.jwks_class = self.jwks_patch.start()
        self.decode = self.decode_patch.start()
        self.env_patch.start()
        self.info_patch.start()

        self.addCleanup(self.jwks_patch.stop)
        self.addCleanup(self.decode_patch.stop)
        self.addCleanup(self.env_patch.stop)
        self.addCleanup(self.info_patch.stop)

    def make_verifier(self):
        signing_key = mock.Mock()
        signing_key.key = "public-key"

        jwks_client = mock.Mock()
        jwks_client.get_signing_key_from_jwt.return_value = signing_key
        self.jwks_class.return_value = jwks_client

        self.decode.return_value = self.CLAIMS
        config = {"issuer": "unittest", "jwks_uri": "unittest"}

        return TokenVerifier(config), jwks_client

    def test_valid_bearer_token_returns_claims(self):
        verifier, jwks_client = self.make_verifier()

        claims = verifier.verify_access_token(
            "Bearer valid-token",
            required_scopes=["search:access"],
        )

        assert claims == self.CLAIMS

        jwks_client.get_signing_key_from_jwt.assert_called_once_with("valid-token")
        self.decode.assert_called_once_with(
            "valid-token",
            "public-key",
            algorithms=["RS256"],
            issuer="unittest",
            audience=["dmis-api"],
            options={"verify_aud": True},
        )

    def test_missing_or_malformed_authorization_header_raises(self):
        verifier, _ = self.make_verifier()

        cases = [
            (None, 401),
            ("Basic abc123", 400),
            ("Bearer ", 400),
        ]

        for authorization, expected_status in cases:
            with self.subTest(authorization=authorization):
                with self.assertRaises(HTTPException) as raised:
                    verifier.verify_access_token(authorization)

                assert raised.exception.status_code == expected_status

        self.decode.assert_not_called()

    def test_invalid_jwt_raises_401(self):
        verifier, _ = self.make_verifier()
        self.decode.side_effect = jwt.InvalidTokenError("invalid token")

        with self.assertRaises(HTTPException) as raised:
            verifier.verify_access_token("Bearer invalid-token")

        assert raised.exception.status_code == 401

    def test_unallowed_or_missing_authorized_party_raises_403(self):
        verifier, _ = self.make_verifier()

        cases = [
            {**self.CLAIMS, "azp": "unknown-client"},
            {key: value for key, value in self.CLAIMS.items() if key != "azp"},
        ]

        for claims in cases:
            with self.subTest(claims=claims):
                self.decode.return_value = claims

                with self.assertRaises(HTTPException) as raised:
                    verifier.verify_access_token("Bearer valid-token")

                assert raised.exception.status_code == 403

    def test_missing_required_scope_raises_403(self):
        verifier, _ = self.make_verifier()
        self.decode.return_value = {
            **self.CLAIMS,
            "scope": "connector:access",
        }

        with self.assertRaises(HTTPException) as raised:
            verifier.verify_access_token(
                "Bearer valid-token",
                required_scopes=["search:access"],
            )

        assert raised.exception.status_code == 403

    def test_multiple_required_scopes_must_all_exist(self):
        verifier, _ = self.make_verifier()
        self.decode.return_value = {
            **self.CLAIMS,
            "scope": "search:access",
        }

        with self.assertRaises(HTTPException) as raised:
            verifier.verify_access_token(
                "Bearer valid-token",
                required_scopes=["search:access", "connector:access"],
            )

        assert raised.exception.status_code == 403
