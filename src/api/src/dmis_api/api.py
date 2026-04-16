"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

from json.decoder import JSONDecodeError
import argparse
from typing import Any
from collections.abc import Sequence

import requests
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dmis_logger import dms_warning, dms_info
from initialisation_tools import read_env_variable, read_port

from .auth import TokenVerifier


class API:
    """Management class for main API."""

    app: FastAPI = FastAPI()

    log_level: str | None = None
    search_api_url: str
    query_api_url: str
    connector_api_url: str
    token_verifier: TokenVerifier

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        search_api_url: str,
        query_api_url: str,
        connector_api_url: str,
        token_verifier: TokenVerifier,
        log_level: str | None = None,
    ) -> None:
        """Constructor."""
        self.app = FastAPI()

        self.log_level = log_level
        self.search_api_url = search_api_url.rstrip("/")
        self.query_api_url = query_api_url.rstrip("/")
        self.connector_api_url = connector_api_url.rstrip("/")
        self.token_verifier = token_verifier

        self.app.add_exception_handler(
            RequestValidationError,
            self.validation_exception_handler,
        )

        self.app.add_api_route("/search_engine/{endpoint}", self.search_engine_get, methods=["GET"])
        self.app.add_api_route("/search_engine/{endpoint}", self.search_engine_post, methods=["POST"])
        self.app.add_api_route("/stochastic-analyzer/{endpoint}", self.stochastic_analyzer_get, methods=["GET"])
        self.app.add_api_route("/stochastic-analyzer/{endpoint}", self.stochastic_analyzer_post, methods=["POST"])
        self.app.add_api_route("/connector/{endpoint}", self.connector_get, methods=["GET"])
        self.app.add_api_route("/connector/{endpoint}", self.connector_post, methods=["POST"])

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
        if host is not None and ("127.0.0.1" in host or "localhost" in host):  # NOTE; THIS MUST BE REMOVED
            return {}
        claims = self.token_verifier.verify_access_token(authorization)
        dms_info(
            f"Authorized request: "
            f"sub={claims.get('sub')} "
            f"user={claims.get('preferred_username')} "
            f"azp={claims.get('azp')}"
        )
        return claims

    async def execute_get_request(self, url: str, request: Request) -> JSONResponse:
        """Execute GET request."""
        try:
            params = dict(request.query_params)
        except TypeError:
            dms_info(f"API retrieved a GET request ({url}) with incorrect param format: {request.query_params}")
            return JSONResponse(status_code=400)

        try:
            response = requests.get(  # noqa: ASYNC210 #Migration from requests will happen in separate commit.
                url,
                params=params,
                timeout=120,
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Request to {url} returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc
        except requests.RequestException as exc:
            dms_warning(f"Request to {url} failed: {exc}")
            raise HTTPException(status_code=502) from exc

        return JSONResponse(status_code=200, content=response_data)

    async def execute_post_request(self, url: str, request: Request) -> JSONResponse:
        """Execute POST request."""
        try:
            body = await request.json()
            params = dict(request.query_params)
        except TypeError:
            params = None
        except JSONDecodeError:
            dms_info(f"API retrieved a POST request ({url}) with incorrect body format: {request.body()}")
            return JSONResponse(status_code=400, content={})

        try:
            response = requests.post(  # noqa: ASYNC210 #Migration from requests will happen in separate commit.
                url,
                params=params,
                json=body,
                timeout=120,
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Request to {url} returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc
        except requests.RequestException as exc:
            dms_warning(f"Request to {url} failed: {exc}")
            raise HTTPException(status_code=502) from exc

        return JSONResponse(status_code=200, content=response_data)

    async def search_engine_get(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """GET request to search engine."""
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_get_request(f"{self.search_api_url}/{endpoint}", request)

    async def search_engine_post(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """POST request to search engine."""
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_post_request(f"{self.search_api_url}/{endpoint}", request)

    async def stochastic_analyzer_get(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """GET request to stochastic analyzer."""
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_get_request(f"{self.query_api_url}/{endpoint}", request)

    async def stochastic_analyzer_post(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """POST request to stochastic analyzer."""
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_post_request(f"{self.query_api_url}/{endpoint}", request)

    async def connector_get(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """GET request to connector API."""
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_get_request(f"{self.connector_api_url}/{endpoint}", request)

    async def connector_post(
        self, endpoint: str, request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """POST request to connector API."""
        self.authorize(authorization, request.headers.get("Referer"))
        return await self.execute_post_request(f"{self.connector_api_url}/{endpoint}", request)


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    bind_address = read_env_variable("DMIS_API_BIND_ADDRESS")
    port = read_port("DMIS_API_PORT")
    search_api_url = read_env_variable("DMIS_API_SEARCH_URL")
    query_api_url = read_env_variable("DMIS_API_QUERY_URL")
    connector_api_url = read_env_variable("DMIS_API_CONNECTOR_URL")
    keycloak_issuer = read_env_variable("DMIS_API_KEYCLOAK_ISSUER")
    keycloak_jwks_url = read_env_variable("DMIS_API_KEYCLOAK_JWKS_URL")
    keycloak_expected_azp = read_env_variable("DMIS_API_KEYCLOAK_EXPECTED_AZP")

    log_level = "debug" if args.dev else None

    token_verifier = TokenVerifier(issuer=keycloak_issuer, jwks_url=keycloak_jwks_url, expected_azp=keycloak_expected_azp)

    api = API(
        search_api_url=search_api_url,
        query_api_url=query_api_url,
        connector_api_url=connector_api_url,
        token_verifier=token_verifier,
        log_level=log_level,
    )

    uvicorn.run(
        api.app,
        host=bind_address,
        port=port,
        log_level=log_level,
    )
