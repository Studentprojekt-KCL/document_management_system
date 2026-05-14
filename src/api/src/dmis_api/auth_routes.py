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


class AuthRoutes:
    """Authentication route handlers."""

    ACCESS_COOKIE_MAX_AGE = int(read_env_variable("DMISAPI_ACCESS_COOKIE_MAX_AGE"))
    REFRESH_COOKIE_MAX_AGE = int(read_env_variable("DMISAPI_REFRESH_COOKIE_MAX_AGE"))
    _session: aiohttp.ClientSession | None

    def __init__(self, token_verifier: Any) -> None:
        self.token_verifier = token_verifier
        self.ad_token_url = read_env_variable("DMISAPI_AD_TOKEN_URL")
        self.ad_logout_url = read_env_variable("DMISAPI_AD_LOGOUT_URL")
        self.dmisapi_client_id = read_env_variable("DMISAPI_AD_CLIENT_ID")
        admin_roles_list = read_env_variable("DMISAPI_ADMIN_ROLES", required=False)
        self.admin_roles = [role.strip() for role in admin_roles_list.split(",") if role.strip()] if admin_roles_list else []

        self._session = None

    async def close_session(self) -> None:
        """Tear down session."""
        if self._session is not None:
            self._session.close()

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

        access_max_age = self._get_token_max_age(token_data, "expires_in", self.ACCESS_COOKIE_MAX_AGE)
        refresh_max_age = self._get_token_max_age(token_data, "refresh_expires_in", self.REFRESH_COOKIE_MAX_AGE)

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
                path="api/auth/refresh",
            )

        if isinstance(id_token, str):
            response.set_cookie(
                key="id_token",
                value=id_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=access_max_age,
                path="api/auth/logout",
            )

    async def _request_tokens(self, data: dict[str, str]) -> dict[str, Any]:
        """Request tokens from AD provider using provided form data."""
        try:
            session = await self.get_session()
            resp = await session.post(
                self.ad_token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = await resp.json()
        except (JSONDecodeError, aiohttp.ContentTypeError) as err:
            dms_warning(f"Recieved response which could not be JSON decoded from {self.ad_token_url}, (err: {err})")
            raise HTTPException(status_code=502) from err  # pylint: disable=W0707
        if resp.status != 200:  # noqa
            dms_warning(f"Recieved unexpected response code ({resp.status}) from {self.ad_token_url}")
            raise HTTPException(status_code=502)
        if not isinstance(response, dict) or "access_token" not in response:
            raise HTTPException(status_code=502)

        return response

    async def check_auth(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Check if user is authenticated."""
        claims = self._verify_cookie_token(access_token)
        if not claims:
            raise HTTPException(status_code=401)

        client_roles = self._get_client_roles(claims)
        if not client_roles:
            raise HTTPException(status_code=403)

        return JSONResponse(
            status_code=200,
            content={
                "authenticated": True,
                "user": {
                    "username": claims.get("preferred_username"),
                },
            },
        )

    def _get_client_roles(self, claims: dict[str, Any]) -> list[str]:
        """Extract client roles for configured client."""
        roles = claims.get("resource_access", {}).get(self.dmisapi_client_id, {}).get("roles", [])
        return roles if isinstance(roles, list) else []

    async def auth_me(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Return authenticated user details and roles."""
        claims = self._verify_cookie_token(access_token)
        if not claims:
            raise HTTPException(status_code=401)

        client_roles = claims.get("resource_access", {}).get(self.dmisapi_client_id, {}).get("roles", [])
        realm_roles = claims.get("realm_access", {}).get("roles", [])

        return JSONResponse(
            status_code=200,
            content={
                "authenticated": True,
                "user": {
                    "username": claims.get("preferred_username"),
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

        client_roles = self._get_client_roles(claims)

        is_admin = any(role in client_roles for role in self.admin_roles)

        return JSONResponse(
            status_code=200,
            content={
                "admin": is_admin,
            },
        )

    async def code_exchange(
        self,
        request: Request,
        code: str = Form(...),
        code_verifier: str = Form(...),
    ) -> JSONResponse:
        """Exchange authorization code for tokens via provided AD."""
        origin = request.headers.get("Origin")
        token_data = await self._request_tokens(
            {
                "grant_type": "authorization_code",
                "client_id": self.dmisapi_client_id,
                "code": code,
                "redirect_uri": f"{origin}/auth/callback",
                "code_verifier": code_verifier,
            }
        )

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
                "client_id": self.dmisapi_client_id,
                "refresh_token": refresh_token,
            }
        )

        response = JSONResponse(
            status_code=200,
            content={"message": "Session refreshed"},
        )
        self._set_auth_cookies(response, token_data)
        return response

    async def logout_auth(self, request: Request, id_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Generate logout URL from AD and clear authentication cookies."""
        post_logout_redirect_uri = request.headers.get("Origin") + "/"

        params = {
            "post_logout_redirect_uri": post_logout_redirect_uri,
            "client_id": self.dmisapi_client_id,
        }
        if id_token:
            params["id_token_hint"] = id_token

        logout_url = f"{self.ad_logout_url}?{urlencode(params)}"
        response = JSONResponse(
            status_code=200,
            content={"logout_url": logout_url},
        )
        response.delete_cookie("access_token", path="/", secure=True, samesite="lax")
        response.delete_cookie("refresh_token", path="api/auth/refresh", secure=True, samesite="lax")
        response.delete_cookie("id_token", path="api/auth/logout", secure=True, samesite="lax")
        return response
