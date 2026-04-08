"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from typing import Any

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from dmis_logger import dms_warning, dms_info


class TokenVerifier:
    """Verify Keycloak bearer access tokens for this API."""

    def __init__(
        self,
        issuer: str,
        jwks_url: str,
        audience: str | None = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwks_client = PyJWKClient(jwks_url)

    def verify_access_token(self, authorization: str | None) -> dict[str, Any]:
        if authorization is None:
            dms_info("Missing Authorization header.")
            raise HTTPException(status_code=401)

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            dms_info("Missing or invalid Authorization header.")
            raise HTTPException(status_code=401)

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            decode_kwargs: dict[str, Any] = {
                "key": signing_key.key,
                "algorithms": ["RS256"],
                "issuer": self.issuer,
            }

            if self.audience:
                decode_kwargs["audience"] = self.audience
            else:
                decode_kwargs["options"] = {"verify_aud": False}

            claims = jwt.decode(token, **decode_kwargs)

        except jwt.InvalidTokenError as exc:
            dms_info(f"Invalid access token: {exc}")
            raise HTTPException(status_code=401) from exc

        azp = claims.get("azp")
        if azp != "dms-frontend":
            dms_info(f"Unexpected azp: {azp!r}")
            raise HTTPException(status_code=403)

        realm_roles = set(claims.get("realm_access", {}).get("roles", []))
        client_roles = set(claims.get("resource_access", {}).get("dms-frontend", {}).get("roles", []))
        all_roles = realm_roles | client_roles

        if "user" not in all_roles and "admin" not in all_roles:
            dms_info(f"Missing required role. realm_roles={sorted(realm_roles)}, client_roles={sorted(client_roles)}")
            raise HTTPException(status_code=403)

        return claims
