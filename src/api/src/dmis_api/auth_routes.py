"""Authentication routes for DMIS API."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import Cookie, Form
from fastapi.responses import JSONResponse

class AuthRoutes:
    """Authentication route handlers."""

    ACCESS_COOKIE_MAX_AGE = 3600
    REFRESH_COOKIE_MAX_AGE = 30 * 24 * 3600

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        token_verifier: Any,
        http_client: httpx.AsyncClient,
        keycloak_token_url: str,
        keycloak_logout_url: str,
        frontend_client_id: str,
        frontend_redirect_uri: str,
    ) -> None:
        self.token_verifier = token_verifier
        self.http_client = http_client
        self.keycloak_token_url = keycloak_token_url
        self.keycloak_logout_url = keycloak_logout_url
        self.frontend_client_id = frontend_client_id
        self.frontend_redirect_uri = frontend_redirect_uri

    def _verify_cookie_token(self, access_token: str | None) -> dict[str, Any] | None:
        """Verify access token from cookie and return claims."""
        if not access_token:
            return None
        try:
            return self.token_verifier.verify_access_token(f"Bearer {access_token}")
        except httpx.HTTPError:
            return None

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
            samesite="none",
            max_age=max_age,
        )

    def _set_auth_cookies(self, response: JSONResponse, token_data: dict[str, Any]) -> None:
        """Set authentication cookies from token response data."""
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        id_token = token_data.get("id_token")

        if isinstance(access_token, str):
            self._set_cookie(response, "access_token", access_token, self.ACCESS_COOKIE_MAX_AGE)
        if isinstance(refresh_token, str):
            self._set_cookie(response, "refresh_token", refresh_token, self.REFRESH_COOKIE_MAX_AGE)
        if isinstance(id_token, str):
            self._set_cookie(response, "id_token", id_token, self.ACCESS_COOKIE_MAX_AGE)

    async def _request_tokens(self, data: dict[str, str]) -> dict[str, Any] | None:
        """Request tokens from Keycloak using provided form data."""
        try:
            resp = await self.http_client.post(
                self.keycloak_token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return None

    def _unauthenticated_response(self) -> JSONResponse:
        """Return a standardized unauthenticated response."""
        return JSONResponse(status_code=401, content={"authenticated": False})

    async def check_auth(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Check if user is authenticated."""
        claims = self._verify_cookie_token(access_token)
        if not claims:
            return self._unauthenticated_response()

        return JSONResponse(
            status_code=200,
            content={
                "authenticated": True,
                "user": {
                    "username": claims.get("preferred_username"),
                },
            },
        )

    async def auth_me(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Return authenticated user details and roles."""
        claims = self._verify_cookie_token(access_token)
        if not claims:
            return self._unauthenticated_response()

        client_roles = (
            claims.get("resource_access", {})
            .get(self.frontend_client_id, {})
            .get("roles", [])
        )
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

    async def code_exchange(
        self,
        code: str = Form(...),
        code_verifier: str = Form(...),
    ) -> JSONResponse:
        """Exchange authorization code for tokens via Keycloak."""
        token_data = await self._request_tokens(
            {
                "grant_type": "authorization_code",
                "client_id": self.frontend_client_id,
                "code": code,
                "redirect_uri": self.frontend_redirect_uri,
                "code_verifier": code_verifier,
            }
        )

        if not token_data:
            return JSONResponse(
                status_code=502,
                content={"message": "Token exchange failed"},
            )

        if not token_data.get("access_token"):
            return JSONResponse(
                status_code=502,
                content={"message": "No access token returned"},
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
                "client_id": self.frontend_client_id,
                "refresh_token": refresh_token,
            }
        )

        if not token_data:
            return JSONResponse(
                status_code=401,
                content={"message": "Refresh failed"},
            )

        if not token_data.get("access_token"):
            return JSONResponse(
                status_code=401,
                content={"message": "No access token returned"},
            )

        response = JSONResponse(
            status_code=200,
            content={"message": "Session refreshed"},
        )
        self._set_auth_cookies(response, token_data)
        return response

    async def logout_auth(self, id_token: str | None = Cookie(default=None)) -> JSONResponse:
        """Generate Keycloak logout URL and clear authentication cookies."""
        post_logout_redirect_uri = self.frontend_redirect_uri.rsplit("/auth/callback", 1)[0] + "/"

        params = {
            "post_logout_redirect_uri": post_logout_redirect_uri,
            "client_id": self.frontend_client_id,
        }
        if id_token:
            params["id_token_hint"] = id_token

        logout_url = f"{self.keycloak_logout_url}?{urlencode(params)}"
        response = JSONResponse(
            status_code=200,
            content={"logout_url": logout_url},
        )
        response.delete_cookie("access_token", path="/", secure=True, samesite="none")
        response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
        response.delete_cookie("id_token", path="/", secure=True, samesite="none")
        return response
