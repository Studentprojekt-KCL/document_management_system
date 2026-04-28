"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from json.decoder import JSONDecodeError
import argparse
from typing import Any
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared_functions.dmis_logger import dms_warning, dms_info
from shared_functions.initialisation_tools import read_env_variable, read_port

from .auth import TokenVerifier


class API:
    """Management class for main API."""

    app: FastAPI = FastAPI()

    log_level: str | None = None
    upstream_urls: dict[str, str]
    token_verifier: TokenVerifier
    http_client: httpx.AsyncClient
    required_scopes: dict[str, list[str]]

    def __init__(
        self,
        upstream_urls: dict[str, str],
        token_verifier: TokenVerifier,
        log_level: str | None = None,
    ) -> None:
        """Constructor."""
        self.app = FastAPI()

        self.log_level = log_level
        self.upstream_urls = {key: value.rstrip("/") for key, value in upstream_urls.items()}
        self.token_verifier = token_verifier
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

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

    def authorize(
        self,
        authorization: str | None,
        host: str | None,
        required_scopes: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Validate bearer token and return claims."""
        if (
            authorization is not None and host is not None and ("127.0.0.1" in host or "localhost" in host)
        ):  # NOTE; THIS MUST BE REMOVED
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

    async def execute_get_request(self, url: str, request: Request, authorization: str | None) -> JSONResponse:
        """Execute GET request."""
        try:
            params = dict(request.query_params)
        except TypeError:
            dms_info(f"API retrieved a GET request ({url}) with incorrect param format: {request.query_params}")
            return JSONResponse(status_code=400)

        try:
            response = await self.http_client.get(url, params=params, headers={"Authorization": authorization})
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
        except TypeError:
            params = None
        except JSONDecodeError:
            dms_info(f"API retrieved a POST request ({url}) with incorrect body format: {await request.body()}")
            return JSONResponse(status_code=400, content={})

        try:
            response = await self.http_client.post(url, params=params, json=body, headers={"Authorization": authorization})
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
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """GET request to search engine."""
        self.authorize(authorization, request.headers.get("Referer"), required_scopes=self.required_scopes["searcheng"])
        return await self.execute_get_request(f"{self.upstream_urls['searcheng']}/{endpoint}", request, authorization)

    async def search_engine_post(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """POST request to search engine."""
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["searcheng"],
        )
        return await self.execute_post_request(f"{self.upstream_urls['searcheng']}/{endpoint}", request, authorization)

    async def stochastic_analyzer_get(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """GET request to stochastic analyzer."""
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["stochan"],
        )
        return await self.execute_get_request(f"{self.upstream_urls['stochan']}/{endpoint}", request, authorization)

    async def stochastic_analyzer_post(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """POST request to stochastic analyzer."""
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["stochan"],
        )
        return await self.execute_post_request(f"{self.upstream_urls['stochan']}/{endpoint}", request, authorization)

    async def connector_get(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """GET request to connector API."""
        self.authorize(
            authorization,
            request.headers.get("Referer"),
            required_scopes=self.required_scopes["congateway"],
        )
        return await self.execute_get_request(f"{self.upstream_urls['congateway']}/{endpoint}", request, authorization)

    async def connector_post(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """POST request to connector API."""
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

    bind_address = read_env_variable("DMISAPI_BIND_ADDR")
    port = read_port("DMISAPI_BIND_PORT")
    keycloak_issuer = read_env_variable("DMISAPI_AD_URL")
    keycloak_jwks_url = read_env_variable("DMISAPI_AD_JWKS_URL")
    audience_raw = read_env_variable("DMISAPI_AD_AUDIENCE", required=False)
    expected_audience = [value.strip() for value in audience_raw.split(",") if value.strip()] if audience_raw else None
    allowed_azp = [value.strip() for value in read_env_variable("DMISAPI_AD_ALLOWED_AZP").split(",") if value.strip()]
    upstream_urls = {
        "searcheng": read_env_variable("DMISAPI_SEARCHENG_URL"),
        "stochan": read_env_variable("DMISAPI_STOCHAN_URL"),
        "congateway": read_env_variable("DMISAPI_CONGATEWAY_URL"),
    }

    log_level = "debug" if args.dev else None

    token_verifier = TokenVerifier(
        issuer=keycloak_issuer,
        jwks_url=keycloak_jwks_url,
        expected_audience=expected_audience,
        allowed_azp=allowed_azp or None,
    )

    api = API(
        upstream_urls=upstream_urls,
        token_verifier=token_verifier,
        log_level=log_level,
    )

    uvicorn.run(
        api.app,
        host=bind_address,
        port=port,
        log_level=log_level,
    )
