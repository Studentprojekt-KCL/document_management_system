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

ROLE_KEYS = {"roles", "role", "permissions", "groups", "authorities"}
HTTP_OK = 200


class AuthRoutes:
    """Authentication route handlers."""

    _session: aiohttp.ClientSession | None

    def __init__(self, token_verifier: Any) -> None:
        self.token_verifier = token_verifier

        self.ad_well_known_url = read_env_variable("DMISAPI_AD_WELL_KNOWN_URL")
        self.user_roles = self._read_csv_env("DMISAPI_USER_ROLES")
        self.admin_roles = self._read_csv_env("DMISAPI_ADMIN_ROLES")
        self.dmisapi_client_id = read_env_variable("DMISAPI_AD_CLIENT_ID")
        self.oidc_config: dict[str, Any] | None = None

        self._session = None

    @staticmethod
    def _read_csv_env(name: str) -> list[str]:
        value = read_env_variable(name, required=False)
        return [item.strip() for item in value.split(",") if item.strip()] if value else []

    async def close_session(self) -> None:
        """Tear down session."""
        if self._session is not None:
            self._session.close()

    async def get_session(self) -> aiohttp.ClientSession:
        """Set up AIO http clinet if not initialized."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

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

        max_age = int(read_env_variable("DMISAPI_ACCESS_COOKIE_MAX_AGE", required=False) or 3600)

        access_max_age = self._get_token_max_age(token_data, "expires_in", max_age)

        cookie_max_age = int(read_env_variable("DMISAPI_REFRESH_COOKIE_MAX_AGE", required=False) or 30 * 24 * 3600)
        refresh_max_age = self._get_token_max_age(token_data, "refresh_expires_in", cookie_max_age)

        if isinstance(access_token, str):
            self._set_cookie(response, "__Secure-access_token", access_token, access_max_age)

        if isinstance(refresh_token, str):
            response.set_cookie(
                key="__Secure-refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=refresh_max_age,
                path="/auth/refresh",
            )

        if isinstance(id_token, str):
            response.set_cookie(
                key="__Secure-id_token",
                value=id_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=access_max_age,
                path="/auth/logout",
            )

    async def _load_openid_endpoints(self) -> None:
        """Load OpenID endpoints from well-known configuration."""
        if self.oidc_config is not None:
            return

        try:
            # Get the big endpoint list from wellknown
            session = await self.get_session()
            resp = await session.get(self.ad_well_known_url)
            config = await resp.json()

        except (JSONDecodeError, aiohttp.ContentTypeError) as err:
            dms_warning(f"Received response which could not be JSON decoded from " f"{self.ad_well_known_url}, (err: {err})")
            raise HTTPException(status_code=502) from err

        if resp.status != HTTP_OK:
            dms_warning(f"Error response: ({resp.status}) from " f"{self.ad_well_known_url}")
            raise HTTPException(status_code=502)

        if not isinstance(config, dict):
            raise HTTPException(status_code=502)

        self.oidc_config = config

    async def _request_tokens(self, data: dict[str, str]) -> dict[str, Any]:
        """Request tokens from AD provider using provided form data."""
        await self._load_openid_endpoints()

        token_url = self.oidc_config["token_endpoint"]  # type: ignore
        if self.oidc_config is None:
            raise HTTPException(status_code=502)

        try:
            session = await self.get_session()
            resp = await session.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = await resp.json()
        except (JSONDecodeError, aiohttp.ContentTypeError) as err:
            dms_warning(f"Received response which could not be JSON decoded from " f"{token_url}, (err: {err})")
            raise HTTPException(status_code=502) from err

        if resp.status != HTTP_OK:
            dms_warning(f"Received unexpected response code ({resp.status}) from {token_url}")
            raise HTTPException(status_code=502)

        if not isinstance(response, dict) or "access_token" not in response:
            raise HTTPException(status_code=502)

        return response

    async def check_auth(self, access_token: str | None = Cookie(default=None, alias="__Secure-access_token")) -> JSONResponse:
        """Verify authentication token is signed and contained in user roles."""
        claims = self.token_verifier.verify_access_token(f"Bearer {access_token}")
        if not claims:
            raise HTTPException(status_code=401)

        roles = self._get_roles(claims)

        if self.user_roles and not any(role in roles for role in self.user_roles):
            raise HTTPException(status_code=403)

        return JSONResponse(status_code=HTTP_OK, content={"authenticated": True})

    def _extract_roles_recursive(self, value: Any) -> list[str]:
        roles: list[str] = []

        if isinstance(value, dict):
            for key, nested_value in value.items():
                key_lower = key.lower()

                if key_lower in ROLE_KEYS:
                    if isinstance(nested_value, list):
                        roles.extend(str(item) for item in nested_value)
                    elif isinstance(nested_value, str):
                        roles.extend(nested_value.split())

                roles.extend(self._extract_roles_recursive(nested_value))

        elif isinstance(value, list):
            for item in value:
                roles.extend(self._extract_roles_recursive(item))

        return roles

    def _get_roles(self, claims: dict[str, Any]) -> list[str]:
        roles = self._extract_roles_recursive(claims)

        return sorted(set(roles))

    async def auth_me(self, access_token: str | None = Cookie(default=None, alias="__Secure-access_token")) -> JSONResponse:
        """Return authenticated user details and roles."""
        claims = self.token_verifier.verify_access_token(f"Bearer {access_token}")
        if not claims:
            raise HTTPException(status_code=401)

        user_roles = self._get_roles(claims)

        return JSONResponse(
            status_code=HTTP_OK,
            content={
                "authenticated": True,
                "user": {
                    "username": claims.get("preferred_username")
                    or claims.get("email")
                    or claims.get("nickname")
                    or claims.get("sub"),
                    "email": claims.get("email"),
                    "roles": user_roles,
                },
            },
        )

    async def check_admin(self, access_token: str | None = Cookie(default=None, alias="__Secure-access_token")) -> JSONResponse:
        """Check if authenticated user has an admin role"""
        claims = self.token_verifier.verify_access_token(f"Bearer {access_token}")
        if not claims:
            raise HTTPException(status_code=401)

        user_roles = self._get_roles(claims)
        is_admin = any(role in user_roles for role in self.admin_roles)

        return JSONResponse(
            status_code=HTTP_OK,
            content={"admin": is_admin},
        )

    async def code_exchange(
        self,
        request: Request,
        code: str = Form(...),
        code_verifier: str = Form(...),
    ) -> JSONResponse:
        """Exchange authorization code for tokens via provided AD."""
        origin = request.headers.get("Origin")
        redirect_uri = f"{origin.rstrip('/')}/auth/callback"
        token_data = await self._request_tokens(
            {
                "grant_type": "authorization_code",
                "client_id": self.dmisapi_client_id,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            }
        )

        response = JSONResponse(
            status_code=HTTP_OK,
            content={"message": "Login successful"},
        )
        self._set_auth_cookies(response, token_data)
        return response

    async def refresh_auth(self, refresh_token: str | None = Cookie(default=None, alias="__Secure-refresh_token")) -> JSONResponse:
        """Refresh session using the refresh token."""
        if not refresh_token:
            return JSONResponse(
                status_code=401,
                content={"message": "Missing refresh token"},
            )

        token_data = await self._request_tokens(
            {
                "grant_type": "refresh_token",
                "client_id": self.dmisapi_client_id,
                "refresh_token": refresh_token,
            }
        )

        response = JSONResponse(
            status_code=HTTP_OK,
            content={"message": "Session refreshed"},
        )
        self._set_auth_cookies(response, token_data)
        return response

    async def logout_auth(
        self,
        request: Request,
        id_token: str | None = Cookie(default=None, alias="__Secure-id_token"),
    ) -> JSONResponse:
        """Generate logout URL from AD and clear authentication cookies."""
        await self._load_openid_endpoints()

        origin = request.headers.get("Origin")
        post_logout_redirect_uri = f"{origin}/" if origin else "/"

        params = {
            "post_logout_redirect_uri": post_logout_redirect_uri,
            "client_id": self.dmisapi_client_id,
        }

        if id_token:
            params["id_token_hint"] = id_token

        logout_endpoint = self.oidc_config.get("end_session_endpoint")  # type: ignore
        if self.oidc_config is None:
            raise HTTPException(status_code=502)

        if not logout_endpoint:
            raise HTTPException(status_code=502)

        logout_url = f"{logout_endpoint}?{urlencode(params)}"

        response = JSONResponse(
            status_code=HTTP_OK,
            content={"logout_url": logout_url},
        )
        response.delete_cookie("__Secure-access_token", path="/", secure=True, samesite="lax")
        response.delete_cookie("__Secure-refresh_token", path="/api/auth/refresh", secure=True, samesite="lax")
        response.delete_cookie("__Secure-id_token", path="/api/auth/logout", secure=True, samesite="lax")
        return response
