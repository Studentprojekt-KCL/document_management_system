"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from typing import Any
from collections.abc import Iterable

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from shared_functions.dmis_logger import dms_info

from shared_functions.initialisation_tools import read_env_variable


class TokenVerifier:
    """Verify OAuth2/OIDC bearer access tokens and enforce audience, azp and scope-based authorization."""

    def __init__(self) -> None:
        """Initialize token verifier with AD settings."""
        self.issuer = read_env_variable("DMISAPI_AD_URL").rstrip("/")
        self.jwks_client = PyJWKClient(read_env_variable("DMISAPI_AD_JWKS_URL"))

        audience = read_env_variable("DMISAPI_AD_AUDIENCE", required=False)
        expected_audience = [value.strip() for value in audience.split(",") if value.strip()] if audience else None
        self.expected_audience = expected_audience

        if expected_audience is None:
            self.expected_audience = None
        elif isinstance(expected_audience, str):
            self.expected_audience = [expected_audience]
        else:
            self.expected_audience = list(expected_audience)

        allowed_azp_raw = read_env_variable("DMISAPI_AD_ALLOWED_AZP", required=False)
        allowed_azp = [value.strip() for value in allowed_azp_raw.split(",") if value.strip()] if allowed_azp_raw else []

        self.allowed_azp = set(allowed_azp) if allowed_azp else None

    def verify_access_token(
        self,
        authorization: str | None,
        required_scopes: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Validate bearer token and return token claims."""

        if authorization is None:
            dms_info("Recieved token with missing authorization header.")
            raise HTTPException(status_code=401)

        scheme, _, token = authorization.partition(" ")
        token = token.strip()

        if scheme.lower() != "bearer" or not token:
            dms_info("Missing or invalid Authorization header.")
            raise HTTPException(status_code=400)

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
            raise HTTPException(status_code=401) from exc

        azp = claims.get("azp")
        if self.allowed_azp is not None and azp not in self.allowed_azp:
            dms_info(f"Unexpected azp: {azp!r}, allowed={sorted(self.allowed_azp)!r}")
            raise HTTPException(status_code=403)

        required_scope_set = set(required_scopes or [])
        token_scope = claims.get("scope", "")
        token_scopes = set(token_scope.split()) if isinstance(token_scope, str) else set()

        if required_scope_set and not required_scope_set.issubset(token_scopes):
            dms_info(
                "Missing required scope. " f"required_scopes={sorted(required_scope_set)}, " f"token_scopes={sorted(token_scopes)}"
            )
            raise HTTPException(status_code=403)

        return claims
