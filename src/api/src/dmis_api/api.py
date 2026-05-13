"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from json.decoder import JSONDecodeError
import argparse
from typing import Any
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

import aiohttp
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Cookie, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared_functions.dmis_logger import dms_warning, dms_info
from shared_functions.initialisation_tools import read_env_variable, read_port

from .auth import TokenVerifier
from .auth_routes import AuthRoutes


class API:
    """Management class for main API."""

    app: FastAPI = FastAPI()

    log_level: str | None = None
    upstream_urls: dict[str, str]
    token_verifier: TokenVerifier
    required_scopes: dict[str, list[str]]

    def __init__(
        self,
        upstream_urls: dict[str, str],
        log_level: str | None = None,
    ) -> None:
        """Constructor."""
        self.app = FastAPI(lifespan=self.lifespan)
        self.log_level = log_level
        self.upstream_urls = upstream_urls

        self.token_verifier = TokenVerifier()
        self.auth_routes = AuthRoutes(token_verifier=self.token_verifier)
        self.http_client = None

        self.app.add_exception_handler(
            RequestValidationError,
            self.validation_exception_handler,
        )

        searcheng_scope_raw = read_env_variable("DMISAPI_SEARCHENG_SCOPE", required=False)
        stochan_scope_raw = read_env_variable("DMISAPI_STOCHAN_SCOPE", required=False)
        congateway_scope_raw = read_env_variable("DMISAPI_CONGATEWAY_SCOPE", required=False)

        self.required_scopes = {
            "searcheng": searcheng_scope_raw.split() if searcheng_scope_raw else [],
            "stochan": stochan_scope_raw.split() if stochan_scope_raw else [],
            "congateway": congateway_scope_raw.split() if congateway_scope_raw else [],
        }

        self.app.add_api_route("/search_engine/{endpoint}", self.search_engine_get, methods=["GET"])
        self.app.add_api_route("/search_engine/{endpoint}", self.search_engine_post, methods=["POST"])
        self.app.add_api_route("/stochastic-analyzer/{endpoint}", self.stochastic_analyzer_get, methods=["GET"])
        self.app.add_api_route("/stochastic-analyzer/{endpoint}", self.stochastic_analyzer_post, methods=["POST"])
        self.app.add_api_route("/connector/{endpoint}", self.connector_get, methods=["GET"])
        self.app.add_api_route("/connector/{endpoint}", self.connector_post, methods=["POST"])

        self.app.add_api_route("/auth/codeExchange", self.auth_routes.code_exchange, methods=["POST"])
        self.app.add_api_route("/auth/check", self.auth_routes.check_auth, methods=["GET"])
        self.app.add_api_route("/auth/checkAdmin", self.auth_routes.check_admin, methods=["GET"])
        self.app.add_api_route("/auth/me", self.auth_routes.auth_me, methods=["GET"])
        self.app.add_api_route("/auth/refresh", self.auth_routes.refresh_auth, methods=["POST"])
        self.app.add_api_route("/auth/logout", self.auth_routes.logout_auth, methods=["POST"])

    def create_http_client(self) -> aiohttp.ClientSession:
        """Create aiohttp client with timeout."""
        return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120.0, sock_connect=10.0))

    @asynccontextmanager
    async def lifespan(self, _: FastAPI) -> AsyncIterator[None]:
        """Manage teardown."""
        self.http_client = self.create_http_client()
        try:
            yield
        finally:
            await self.auth_routes.close_session()
            if self.http_client is not None:
                await self.http_client.close()

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict[str, Any] = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"

        return JSONResponse(status_code=422, content=content)

    def authorize(
        self,
        authorization: str | None,
        host: str | None,
        required_scopes: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Validate bearer token and return claims."""
        if (
            authorization is not None and host is not None and ("127.0.0.1" in host or "localhost" in host)
        ):  # NOTE; THIS MUST BE REMOVED LATER
            return {}
        claims = self.token_verifier.verify_access_token(
            authorization,
            required_scopes=required_scopes,
        )
        dms_info(
            f"Authorized request: "
            f"sub={claims.get('sub')} "
            f"user={claims.get('preferred_username')} "
            f"azp={claims.get('azp')}"
        )
        return claims

    def resolve_authorization(
        self,
        access_token: str | None,
    ) -> str | None:
        """Resolve Authorization header, falling back to access token cookie."""
        if access_token:
            return f"Bearer {access_token}"
        return None

    async def execute_get_request(self, url: str, request: Request, authorization: str | None) -> Any:
        """Execute GET request."""
        try:
            params = dict(request.query_params)
        except TypeError:
            dms_info(f"API retrieved a GET request ({url}) with incorrect param format: {request.query_params}")
            return JSONResponse(status_code=400, content={})

        headers = {"Authorization": authorization} if authorization else {}

        if self.http_client is None:
            raise HTTPException(status_code=500)

        try:
            async with self.http_client.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                content: Any
                if content_type == "json":
                    content = await response.json()
                else:
                    content = await response.read()
                return Response(content=content, media_type=content_type)
        except JSONDecodeError as exc:
            dms_warning(f"Request to {url} returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc
        except aiohttp.ClientError as exc:
            dms_warning(f"Request to {url} failed: {exc}")
            raise HTTPException(status_code=502) from exc

    async def execute_post_request(self, url: str, request: Request, authorization: str | None) -> Any:
        """Execute POST request."""
        try:
            body = await request.json()
            params = dict(request.query_params)
        except TypeError:
            params = None
        except JSONDecodeError:
            dms_info(f"API retrieved a POST request ({url}) with incorrect body format: {await request.body()}")
            return JSONResponse(status_code=400, content={})

        headers = {"Authorization": authorization} if authorization else {}

        if self.http_client is None:
            raise HTTPException(status_code=500)

        try:
            async with self.http_client.post(url, params=params, json=body, headers=headers) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                content: Any
                if content_type == "json":
                    content = await response.json()
                else:
                    content = await response.read()
                return Response(content=content, media_type=content_type)
        except JSONDecodeError as exc:
            dms_warning(f"Request to {url} returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc
        except aiohttp.ClientError as exc:
            dms_warning(f"Request to {url} failed: {exc}")
            raise HTTPException(status_code=502) from exc

    async def search_engine_get(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """GET request to search engine."""
        authorization = self.resolve_authorization(access_token)
        self.authorize(authorization, request.headers.get("Referer"), required_scopes=self.required_scopes["searcheng"])
        return await self.execute_get_request(f"{self.upstream_urls['searcheng']}/{endpoint}", request, authorization)

    async def search_engine_post(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """POST request to search engine."""
        authorization = self.resolve_authorization(access_token)
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["searcheng"],
        )
        return await self.execute_post_request(f"{self.upstream_urls['searcheng']}/{endpoint}", request, authorization)

    async def stochastic_analyzer_get(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """GET request to stochastic analyzer."""
        authorization = self.resolve_authorization(access_token)
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["stochan"],
        )
        return await self.execute_get_request(f"{self.upstream_urls['stochan']}/{endpoint}", request, authorization)

    async def stochastic_analyzer_post(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """POST request to stochastic analyzer."""
        authorization = self.resolve_authorization(access_token)
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["stochan"],
        )
        return await self.execute_post_request(f"{self.upstream_urls['stochan']}/{endpoint}", request, authorization)

    async def connector_get(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """GET request to connector API."""
        authorization = self.resolve_authorization(access_token)
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["congateway"],
        )
        return await self.execute_get_request(f"{self.upstream_urls['congateway']}/{endpoint}", request, authorization)

    async def connector_post(
        self,
        endpoint: str,
        request: Request,
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        """POST request to connector API."""
        authorization = self.resolve_authorization(access_token)
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["congateway"],
        )
        return await self.execute_post_request(f"{self.upstream_urls['congateway']}/{endpoint}", request, authorization)


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    upstream_urls = {
        "searcheng": read_env_variable("DMISAPI_SEARCHENG_URL").rstrip("/"),
        "stochan": read_env_variable("DMISAPI_STOCHAN_URL").rstrip("/"),
        "congateway": read_env_variable("DMISAPI_CONGATEWAY_URL").rstrip("/"),
    }

    log_level = "debug" if args.dev else None
    api = API(upstream_urls=upstream_urls, log_level=log_level)

    uvicorn.run(
        api.app,
        host=read_env_variable("DMISAPI_BIND_ADDR"),
        port=read_port("DMISAPI_BIND_PORT"),
        log_level=log_level,
    )
