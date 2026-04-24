"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from json.decoder import JSONDecodeError
import argparse
from typing import Any
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Header, Cookie
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from shared_functions.dmis_logger import dms_warning, dms_info
from shared_functions.initialisation_tools import read_env_variable, read_port
from .auth import TokenVerifier
from .auth_routes import AuthRoutes
from .state_routes import StateRoutes

class API:
    """Management class for main API."""

    app: FastAPI = FastAPI()

    log_level: str | None = None
    search_api_url: str
    query_api_url: str
    connector_api_url: str
    token_verifier: TokenVerifier
    http_client: httpx.AsyncClient

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        search_api_url: str,
        query_api_url: str,
        connector_api_url: str,
        token_verifier: TokenVerifier,
        keycloak_token_url: str,
        frontend_client_id: str,
        frontend_redirect_uri: str,
        keycloak_logout_url: str,
        log_level: str | None = None,
    ):
        """Constructor."""
        self.app = FastAPI()

        origins = ["http://localhost:8080"]

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.log_level = log_level
        self.search_api_url = search_api_url.rstrip("/")
        self.query_api_url = query_api_url.rstrip("/")
        self.connector_api_url = connector_api_url.rstrip("/")
        self.token_verifier = token_verifier
        self.keycloak_token_url = keycloak_token_url
        self.keycloak_logout_url = keycloak_logout_url
        self.frontend_client_id = frontend_client_id
        self.frontend_redirect_uri = frontend_redirect_uri
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

        self.auth_routes = AuthRoutes(
            token_verifier=self.token_verifier,
            http_client=self.http_client,
            keycloak_token_url=self.keycloak_token_url,
            keycloak_logout_url=self.keycloak_logout_url,
            frontend_client_id=self.frontend_client_id,
            frontend_redirect_uri=self.frontend_redirect_uri,
        )
        self.state_routes = StateRoutes(token_verifier=self.token_verifier)

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

        self.app.add_api_route("/search_engine/{endpoint}", self.search_engine_get, methods=["GET"])
        self.app.add_api_route("/search_engine/{endpoint}", self.search_engine_post, methods=["POST"])
        self.app.add_api_route("/stochastic-analyzer/{endpoint}", self.stochastic_analyzer_get, methods=["GET"])
        self.app.add_api_route("/stochastic-analyzer/{endpoint}", self.stochastic_analyzer_post, methods=["POST"])
        self.app.add_api_route("/connector/{endpoint}", self.connector_get, methods=["GET"])
        self.app.add_api_route("/connector/{endpoint}", self.connector_post, methods=["POST"])

        self.app.add_api_route("/auth/codeExchange", self.auth_routes.code_exchange, methods=["POST"])
        self.app.add_api_route("/auth/check", self.auth_routes.check_auth, methods=["GET"])
        self.app.add_api_route("/auth/me", self.auth_routes.auth_me, methods=["GET"])
        self.app.add_api_route("/auth/refresh", self.auth_routes.refresh_auth, methods=["POST"])
        self.app.add_api_route("/auth/logout", self.auth_routes.logout_auth, methods=["GET"])

        self.app.add_api_route("/state", self.state_routes.get_state, methods=["GET"])
        self.app.add_api_route("/state", self.state_routes.put_state, methods=["PUT"])
        self.app.add_api_route("/state", self.state_routes.delete_state, methods=["DELETE"])

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """Manage teardown."""
        try:
            yield
        finally:
            await self.http_client.aclose()

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, Any] = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"
        return JSONResponse(status_code=422, content=content)

    def authorize(self, authorization: str | None, host: str | None) -> dict[str, Any]:
        """Validate bearer token and return claims."""
        if authorization is not None and host is not None and ("127.0.0.1" in host or "localhost" in host):
            return {}
        claims = self.token_verifier.verify_access_token(authorization)
        dms_info(
            f"Authorized request: "
            f"sub={claims.get('sub')} "
            f"user={claims.get('preferred_username')} "
            f"azp={claims.get('azp')}"
        )
        return claims

    async def execute_get_request(self, url: str, request: Request, authorization: str | None) -> JSONResponse:
        """Execute GET request."""
        try:
            params = dict(request.query_params)
        except TypeError:
            dms_info(f"API retrieved a GET request ({url}) with incorrect param format: {request.query_params}")
            return JSONResponse(status_code=400)

        try:
            response = await self.http_client.get(
                url,
                params=params,
                headers={"Authorization": authorization},
            )
            response.raise_for_status()
            response_data = response.json()
        except JSONDecodeError as exc:
            dms_warning(f"Request to {url} returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc
        except httpx.HTTPError as exc:
            dms_warning(f"Request to {url} failed: {exc}")
            raise HTTPException(status_code=502) from exc

        return JSONResponse(status_code=200, content=response_data)

    async def execute_post_request(self, url: str, request: Request, authorization: str | None) -> JSONResponse:
        """Execute POST request."""
        try:
            body = await request.json()
            params = dict(request.query_params)
        except Exception:
            params = None
            body = {}

        try:
            response = await self.http_client.post(
                url,
                json=body,
                params=params,
                headers={"Authorization": authorization},
            )
            response.raise_for_status()
            response_data = response.json()
        except JSONDecodeError as exc:
            dms_warning(f"Request to {url} returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc
        except httpx.HTTPError as exc:
            dms_warning(f"Request to {url} failed: {exc}")
            raise HTTPException(status_code=502) from exc

        return JSONResponse(status_code=200, content=response_data)

    async def search_engine_get(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """GET request to search engine."""
        authorization = self.cookie_authorization(access_token)
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_get_request(f"{self.search_api_url}/{endpoint}", request, authorization)

    async def search_engine_post(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """POST request to search engine."""
        authorization = self.cookie_authorization(access_token)
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_post_request(f"{self.search_api_url}/{endpoint}", request, authorization)

    async def stochastic_analyzer_get(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """GET request to stochastic analyzer."""
        authorization = self.cookie_authorization(access_token)
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_get_request(f"{self.query_api_url}/{endpoint}", request, authorization)

    async def stochastic_analyzer_post(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """POST request to stochastic analyzer."""
        authorization = self.cookie_authorization(access_token)
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_post_request(f"{self.query_api_url}/{endpoint}", request, authorization)

    async def connector_get(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """GET request to connector API."""
        authorization = self.cookie_authorization(access_token)
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_get_request(f"{self.connector_api_url}/{endpoint}", request, authorization)

    async def connector_post(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """POST request to connector API."""
        authorization = self.cookie_authorization(access_token)
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_post_request(f"{self.connector_api_url}/{endpoint}", request, authorization)
    
    def cookie_authorization(self, access_token: str | None) -> str:
        if not access_token:
            raise HTTPException(status_code=401, detail="Missing access token cookie")
        return f"Bearer {access_token}"


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    bind_address = read_env_variable("DMISAPI_BIND_ADDR")
    port = read_port("DMISAPI_BIND_PORT")
    search_api_url = read_env_variable("DMISAPI_SEARCHENG_URL")
    query_api_url = read_env_variable("DMISAPI_STOCHAN_URL")
    connector_api_url = read_env_variable("DMISAPI_CONGATEWAY_URL")
    keycloak_issuer = read_env_variable("DMISAPI_AD_URL")
    keycloak_jwks_url = read_env_variable("DMISAPI_AD_JWKS_URL")
    keycloak_expected_azp = read_env_variable("DMISAPI_AD_AUTHORIZED_PARTY")
    frontend_client_id = read_env_variable("FRONTEND_AD_CLIENT_ID")
    frontend_redirect_uri = read_env_variable("FRONTEND_REDIRECT_URI")
    keycloak_token_url = read_env_variable("DMISAPI_AD_TOKEN_URL")
    keycloak_logout_url = read_env_variable("DMISAPI_AD_LOGOUT_URL")

    log_level = "debug" if args.dev else None
    token_verifier = TokenVerifier(
        issuer=keycloak_issuer,
        jwks_url=keycloak_jwks_url,
        expected_azp=keycloak_expected_azp,
    )

    api = API(
        search_api_url=search_api_url,
        query_api_url=query_api_url,
        connector_api_url=connector_api_url,
        token_verifier=token_verifier,
        log_level=log_level,
        frontend_client_id=frontend_client_id,
        frontend_redirect_uri=frontend_redirect_uri,
        keycloak_token_url=keycloak_token_url,
        keycloak_logout_url=keycloak_logout_url,
    )

    uvicorn.run(api.app, host=bind_address, port=port, log_level=log_level)