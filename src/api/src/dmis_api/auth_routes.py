"""Authentication routes for DMIS API."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode
from json.decoder import JSONDecodeError

import aiohttp
from fastapi import Cookie, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from shared_functions.initialisation_tools import read_env_variable
from shared_functions.dmis_logger import dms_warning

HTTP_OK = 200


class AuthRoutes:
    """Authentication route handlers."""

    _session: aiohttp.ClientSession | None

    def __init__(self, token_verifier: Any) -> None:
        self.token_verifier = token_verifier
        self.issuer_url = read_env_variable("DMISAPI_AD_URL").rstrip("/")
        self.config = {
            "client_id": read_env_variable("DMISAPI_AD_CLIENT_ID"),
            "admin_roles": self._read_csv_env("DMISAPI_ADMIN_ROLES"),
            "user_roles": self._read_csv_env("DMISAPI_USER_ROLES"),
            "role_strategy": self._read_string_env("DMISAPI_ROLE_STRATEGY", "keycloak").lower(),
            "access_cookie_max_age": self._read_int_env("DMISAPI_ACCESS_COOKIE_MAX_AGE", 300),
            "refresh_cookie_max_age": self._read_int_env("DMISAPI_REFRESH_COOKIE_MAX_AGE", 1800),
        }
        self._metadata: dict[str, Any] | None = None
        self._session = None

    def _read_csv_env(self, key: str) -> set[str]:
        env_raw = read_env_variable(key, required=False)

        if not env_raw:
            return set()

        return {value.strip() for value in env_raw.split(",") if value.strip()}

    def _read_string_env(self, key: str, default: str) -> str:
        return read_env_variable(key, required=False) or default

    def _read_int_env(self, key: str, default: int) -> int:
        env_raw = read_env_variable(key, required=False)

        if not env_raw:
            return default

        return int(env_raw)

    async def close_session(self) -> None:
        """Tear down session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def get_session(self) -> aiohttp.ClientSession:
        """Set up AIO http client if not initialized."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        return self._session

    async def _get_metadata(self) -> dict[str, Any]:
        """Fetch OIDC metadata (Endpoints for later use such as authroziation, logout)."""
        if self._metadata is not None:
            return self._metadata

        discovery_url = f"{self.issuer_url}/.well-known/openid-configuration"
        session = await self.get_session()

        async with session.get(discovery_url) as response:
            if response.status != HTTP_OK:
                raise HTTPException(
                    status_code=502,
                    detail="Failed to load OIDC discovery document",
                )

            metadata = await response.json()

        self._metadata = metadata
        return metadata

    async def _token_endpoint(self) -> str:
        """Return OIDC token endpoint."""
        metadata = await self._get_metadata()
        return metadata["token_endpoint"]

    async def _logout_endpoint(self) -> str | None:
        """Return OIDC logout endpoint."""
        metadata = await self._get_metadata()
        return metadata.get("end_session_endpoint")

    def _get_origin(self, request: Request) -> str:
        """Get request origin."""
        origin = request.headers.get("Origin")

        if not origin:
            raise HTTPException(status_code=403, detail="Missing origin")

        return origin.rstrip("/")

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
        """Get token max age from token response."""
        max_age = token_data.get(key)
        return max_age if isinstance(max_age, int) else fallback

    def _set_auth_cookies(self, response: JSONResponse, token_data: dict[str, Any]) -> None:
        """Set authentication cookies from token response data."""
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        id_token = token_data.get("id_token")

        access_max_age = self._get_token_max_age(
            token_data,
            "expires_in",
            self.config["access_cookie_max_age"],
        )
        refresh_max_age = self._get_token_max_age(
            token_data,
            "refresh_expires_in",
            self.config["refresh_cookie_max_age"],
        )

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
        token_url = await self._token_endpoint()

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

        if resp.status != HTTP_OK:
            dms_warning(f"Received unexpected response code ({resp.status}) from {token_url}: {response}")
            raise HTTPException(status_code=502)

        if not isinstance(response, dict) or "access_token" not in response:
            raise HTTPException(status_code=502)

        return response

    async def check_auth(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Check if yser us authenticated."""
        claims = self._verify_cookie_token(access_token)

        if not claims:
            raise HTTPException(status_code=401)

        if not self._has_user_access(claims):
            raise HTTPException(status_code=403)

        return JSONResponse(
            status_code=HTTP_OK,
            content={
                "authenticated": True,
                "user": {
                    "username": claims.get("preferred_username") or claims.get("name"),
                },
            },
        )

    def _extract_roles(self, claims: dict[str, Any]) -> set[str]:
        """Extract roles from token claims."""
        roles: set[str] = set()

        if self.config["role_strategy"] == "keycloak":
            keycloak_client_roles = claims.get("resource_access", {}).get(self.config["client_id"], {}).get("roles", [])

            if isinstance(keycloak_client_roles, list):
                roles.update(str(role) for role in keycloak_client_roles)

        elif self.config["role_strategy"] == "entra":
            entra_roles = claims.get("roles", [])

            if isinstance(entra_roles, list):
                roles.update(str(role) for role in entra_roles)

        else:
            raise HTTPException(status_code=500, detail="Invalid role strategy")

        return roles

    def _has_user_access(self, claims: dict[str, Any]) -> bool:
        """Check if user has access to the application."""
        roles = self._extract_roles(claims)

        if not self.config["user_roles"]:
            return bool(roles)

        return bool(roles & self.config["user_roles"])

    async def auth_me(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Return authenticated user details and roles."""
        claims = self._verify_cookie_token(access_token)

        if not claims:
            raise HTTPException(status_code=401)

        client_roles = sorted(self._extract_roles(claims))
        realm_roles = sorted(claims.get("realm_access", {}).get("roles", []))

        return JSONResponse(
            status_code=HTTP_OK,
            content={
                "authenticated": True,
                "user": {
                    "username": claims.get("preferred_username") or claims.get("name"),
                    "email": claims.get("email"),
                    "client_roles": client_roles,
                    "realm_roles": realm_roles,
                },
            },
        )

    async def check_admin(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Check if authenticated user has an admin role"""
        claims = self._verify_cookie_token(access_token)

        if not claims:
            raise HTTPException(status_code=401)

        return JSONResponse(
            status_code=HTTP_OK,
            content={
                "admin": self._is_admin(claims),
            },
        )

    def _is_admin(self, claims: dict[str, Any]) -> bool:
        """Check if user has admin role."""
        roles = self._extract_roles(claims)
        return bool(roles & self.config["admin_roles"])

    async def code_exchange(
        self,
        request: Request,
        code: str = Form(...),
        code_verifier: str = Form(...),
    ) -> JSONResponse:
        """Exchange authorization code for tokens via provided AD."""
        origin = self._get_origin(request)

        token_data = await self._request_tokens(
            {
                "grant_type": "authorization_code",
                "client_id": self.config["client_id"],
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
            status_code=HTTP_OK,
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
                "client_id": self.config["client_id"],
                "refresh_token": refresh_token,
            }
        )

        response = JSONResponse(
            status_code=HTTP_OK,
            content={"message": "Session refreshed"},
        )
        self._set_auth_cookies(response, token_data)
        return response

    async def logout_auth(self, request: Request, id_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Generate logout URL from AD and clear authentication cookies."""
        origin = self._get_origin(request)
        post_logout_redirect_uri = origin + "/"

        logout_endpoint = await self._logout_endpoint()
        logout_url = "/"

        if logout_endpoint:
            params = {
                "post_logout_redirect_uri": post_logout_redirect_uri,
                "client_id": self.config["client_id"],
            }

            if id_token:
                params["id_token_hint"] = id_token

            logout_url = f"{logout_endpoint}?{urlencode(params)}"

        response = JSONResponse(
            status_code=HTTP_OK,
            content={"logout_url": logout_url},
        )

        response.delete_cookie("access_token", path="/", secure=True, samesite="lax")
        response.delete_cookie("refresh_token", path="/api/auth/refresh", secure=True, samesite="lax")
        response.delete_cookie("id_token", path="/api/auth/logout", secure=True, samesite="lax")

        return response
