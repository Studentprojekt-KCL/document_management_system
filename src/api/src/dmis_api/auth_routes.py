"""Authentication routes for DMIS API."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode
from json.decoder import JSONDecodeError

import aiohttp
from fastapi import Cookie, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from .oidc_config import OidcConfig

from shared_functions.initialisation_tools import read_env_variable
from shared_functions.dmis_logger import dms_warning


class AuthRoutes:
    """Authentication route handlers."""

    _session: aiohttp.ClientSession | None

    def __init__(self, token_verifier: Any) -> None:
        self.token_verifier = token_verifier
        self.oidc = OidcConfig()
        self.client_id = self.oidc.client_id
        admin_roles_list = read_env_variable("DMISAPI_ADMIN_ROLES", required=False)
        self.admin_roles = {role.strip() for role in admin_roles_list.split(",") if role.strip()} if admin_roles_list else set()
        user_roles_list = read_env_variable("DMISAPI_USER_ROLES", required=False)
        self.user_roles = {role.strip() for role in user_roles_list.split(",") if role.strip()} if user_roles_list else set()
        allowed_origin_raw = read_env_variable("DMISAPI_ALLOWED_ORIGINS")
        self.allowed_origins = {origin.strip().rstrip("/") for origin in allowed_origin_raw.split(",") if origin.strip()}
        role_strategy = read_env_variable("DMISAPI_ROLE_STRATEGY", required=False) or "keycloak"
        self.role_strategy = role_strategy.strip().lower()

        scope_claim = read_env_variable("DMISAPI_SCOPE_CLAIM", required=False)
        self.scope_claim = scope_claim.strip() if scope_claim else None

        self.access_cookie_max_age = int(
            read_env_variable(
                "DMISAPI_ACCESS_COOKIE_MAX_AGE",
                required=False,
            )
            or "300"
        )

        self.refresh_cookie_max_age = int(
            read_env_variable(
                "DMISAPI_REFRESH_COOKIE_MAX_AGE",
                required=False,
            )
            or "1800"
        )
        self._session = None

    async def close_session(self) -> None:
        """Tear down session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def get_session(self) -> aiohttp.ClientSession:
        """Set up AIO http clinet if not initialized."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _verify_cookie_token(self, access_token: str | None) -> dict[str, Any] | None:
        """Verify access token from cookie and return claims."""
        if not access_token:
            return None

        return self.token_verifier.verify_access_token(f"Bearer {access_token}")

    def _set_cookie(
        self,
        response: JSONResponse,
        key: str,
        value: str,
        max_age: int,
    ) -> None:
        """Set an HTTP-only authentication cookie on the response."""
        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=max_age,
        )

    def _get_token_max_age(
        self,
        token_data: dict[str, Any],
        key: str,
        fallback: int,
    ) -> int:
        """Get token max age from tokens form AD"""
        max_age = token_data.get(key)
        return max_age if isinstance(max_age, int) else fallback

    def _set_auth_cookies(self, response: JSONResponse, token_data: dict[str, Any]) -> None:
        """Set authentication cookies from token response data."""
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        id_token = token_data.get("id_token")

        access_max_age = self._get_token_max_age(token_data, "expires_in", self.access_cookie_max_age)
        refresh_max_age = self._get_token_max_age(token_data, "refresh_expires_in", self.refresh_cookie_max_age)

        if isinstance(access_token, str):
            self._set_cookie(response, "access_token", access_token, access_max_age)

        if isinstance(refresh_token, str):
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=refresh_max_age,
                path="/api/auth/refresh",
            )

        if isinstance(id_token, str):
            response.set_cookie(
                key="id_token",
                value=id_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=access_max_age,
                path="/api/auth/logout",
            )

    async def _request_tokens(self, data: dict[str, str]) -> dict[str, Any]:
        """Request tokens from OIDC provider using provided form data."""
        token_url = await self.oidc.token_endpoint()

        try:
            session = await self.get_session()
            resp = await session.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = await resp.json()
        except (JSONDecodeError, aiohttp.ContentTypeError) as err:
            dms_warning(f"Received response which could not be JSON decoded from {token_url}, err: {err}")
            raise HTTPException(status_code=502) from err

        if resp.status != 200:
            dms_warning(f"Received unexpected response code ({resp.status}) from {token_url}: {response}")
            raise HTTPException(status_code=502)

        if not isinstance(response, dict) or "access_token" not in response:
            raise HTTPException(status_code=502)

        return response

    async def check_auth(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        claims = self._verify_cookie_token(access_token)

        if not claims:
            raise HTTPException(status_code=401)

        if not self._has_user_access(claims):
            raise HTTPException(status_code=403)

        return JSONResponse(
            status_code=200,
            content={
                "authenticated": True,
                "user": {
                    "username": claims.get("preferred_username") or claims.get("name"),
                },
            },
        )

    def _extract_roles(self, claims: dict[str, Any]) -> set[str]:
        roles: set[str] = set()

        if self.role_strategy == "keycloak":
            keycloak_client_roles = claims.get("resource_access", {}).get(self.client_id, {}).get("roles", [])

            if isinstance(keycloak_client_roles, list):
                roles.update(str(role) for role in keycloak_client_roles)

        elif self.role_strategy == "entra":
            entra_roles = claims.get("roles", [])

            if isinstance(entra_roles, list):
                roles.update(str(role) for role in entra_roles)

        else:
            raise HTTPException(status_code=500, detail="Invalid role strategy")

        return roles

    def _has_user_access(self, claims: dict[str, Any]) -> bool:
        roles = self._extract_roles(claims)

        if not self.user_roles:
            return bool(roles)

        return bool(roles & self.user_roles)

    async def auth_me(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Return authenticated user details and roles."""
        claims = self._verify_cookie_token(access_token)

        if not claims:
            raise HTTPException(status_code=401)

        roles = sorted(self._extract_roles(claims))

        return JSONResponse(
            status_code=200,
            content={
                "authenticated": True,
                "user": {
                    "username": claims.get("preferred_username") or claims.get("name"),
                    "email": claims.get("email"),
                    "roles": roles,
                },
            },
        )

    async def check_admin(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Check if authenticated user has an admin role."""
        claims = self._verify_cookie_token(access_token)

        if not claims:
            raise HTTPException(status_code=401)

        return JSONResponse(
            status_code=200,
            content={
                "admin": self._is_admin(claims),
            },
        )

    def _is_admin(self, claims: dict[str, Any]) -> bool:
        roles = self._extract_roles(claims)
        return bool(roles & self.admin_roles)

    async def code_exchange(self, request: Request, code: str = Form(...), code_verifier: str = Form(...)) -> JSONResponse:
        """Exchange authorization code for tokens via provided AD."""
        origin = self._validate_origin(request)
        token_data = await self._request_tokens(
            {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": code,
                "redirect_uri": f"{origin}/auth/callback",
                "code_verifier": code_verifier,
            }
        )

        access_token = token_data.get("access_token")

        if not isinstance(access_token, str):
            raise HTTPException(status_code=502, detail="Missing access token")

        claims = self.token_verifier.verify_access_token(f"Bearer {access_token}")
        if not self._has_user_access(claims):
            raise HTTPException(status_code=403, detail="User does not have access to this application")

        response = JSONResponse(
            status_code=200,
            content={"message": "Login successful"},
        )
        self._set_auth_cookies(response, token_data)
        return response

    async def refresh_auth(self, refresh_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Refresh session using the refresh token."""
        if not refresh_token:
            return JSONResponse(
                status_code=401,
                content={"message": "Missing refresh token"},
            )

        token_data = await self._request_tokens(
            {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "refresh_token": refresh_token,
            }
        )

        response = JSONResponse(
            status_code=200,
            content={"message": "Session refreshed"},
        )
        self._set_auth_cookies(response, token_data)
        return response

    def _validate_origin(self, request: Request) -> str:
        """Validate request Origin against allowed frontend origin."""
        origin = request.headers.get("Origin")

        if not origin:
            raise HTTPException(status_code=403, detail="missing origin")

        normalized_origin = origin.rstrip("/")

        if normalized_origin not in self.allowed_origins:
            raise HTTPException(status_code=403, detail="Invalid origin")

        return normalized_origin

    async def logout_auth(self, request: Request, id_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Generate logout URL from AD and clear authentication cookies."""
        origin = self._validate_origin(request)
        post_logout_redirect_uri = origin + "/"

        logout_endpoint = await self.oidc.logout_endpoint()

        logout_url = "/"

        if logout_endpoint:
            params = {
                "post_logout_redirect_uri": post_logout_redirect_uri,
                "client_id": self.client_id,
            }

            if id_token:
                params["id_token_hint"] = id_token

            logout_url = f"{logout_endpoint}?{urlencode(params)}"

        response = JSONResponse(
            status_code=200,
            content={"logout_url": logout_url},
        )

        response.delete_cookie(
            "access_token",
            path="/",
            secure=True,
            samesite="lax",
        )

        response.delete_cookie(
            "refresh_token",
            path="/api/auth/refresh",
            secure=True,
            samesite="lax",
        )

        response.delete_cookie(
            "id_token",
            path="/api/auth/logout",
            secure=True,
            samesite="lax",
        )
        return response
