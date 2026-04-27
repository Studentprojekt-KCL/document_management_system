"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from typing import Any
from collections.abc import Iterable

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from shared_functions.dmis_logger import dms_info


class TokenVerifier:
    """Verify OAuth2/OIDC bearer access tokens and enforce audience, azp and scope-based authorization."""

    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals
        self,
        issuer: str,
        jwks_url: str,
        expected_audience: str | Iterable[str] | None = None,
        allowed_azp: Iterable[str] | None = None,
    ) -> None:
        """Initialize token verifier with Keycloak settings."""
        self.issuer = issuer.rstrip("/")
        self.jwks_client = PyJWKClient(jwks_url)
        if expected_audience is None:
            self.expected_audience = None
        elif isinstance(expected_audience, str):
            self.expected_audience = [expected_audience]
        else:
            self.expected_audience = list(expected_audience)
        self.allowed_azp = set(allowed_azp) if allowed_azp else None

    def verify_access_token(
        self,
        authorization: str | None,
        required_scopes: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Validate bearer token and return token claims."""

        if authorization is None:
            dms_info("Missing Authorization header.")
            raise HTTPException(
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        scheme, _, token = authorization.partition(" ")
        token = token.strip()

        if scheme.lower() != "bearer" or not token:
            dms_info("Missing or invalid Authorization header.")
            raise HTTPException(
                status_code=400,
                headers={
                    "WWW-Authenticate": (
                        'Bearer error="invalid_request", ' 'error_description="Missing or invalid Authorization header."'
                    )
                },
            )

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.expected_audience,
                options={"verify_aud": self.expected_audience is not None},
            )
        except jwt.InvalidTokenError as exc:
            dms_info(f"Invalid access token: {exc}")
            raise HTTPException(
                status_code=401,
                headers={
                    "WWW-Authenticate": (
                        'Bearer error="invalid_token", ' 'error_description="The access token is invalid or expired."'
                    )
                },
            ) from exc

        azp = claims.get("azp")
        if self.allowed_azp is not None and azp not in self.allowed_azp:
            dms_info(f"Unexpected azp: {azp!r}, allowed={sorted(self.allowed_azp)!r}")
            raise HTTPException(
                status_code=403,
                headers={
                    "WWW-Authenticate": (
                        'Bearer error="insufficient_scope", '
                        'error_description="The access token is not authorized for this client." '
                    )
                },
            )

        required_scope_set = set(required_scopes or [])
        token_scope = claims.get("scope", "")
        token_scopes = set(token_scope.split()) if isinstance(token_scope, str) else set()

        if required_scope_set and not required_scope_set.issubset(token_scopes):
            dms_info(
                "Missing required scope. " f"required_scopes={sorted(required_scope_set)}, " f"token_scopes={sorted(token_scopes)}"
            )
            raise HTTPException(
                status_code=403,
                headers={
                    "WWW-Authenticate": (
                        'Bearer error="insufficient_scope", '
                        f'scope="{" ".join(sorted(required_scope_set))}", '
                        'error_description="The access token lacks required scope."'
                    )
                },
            )

        return claims
