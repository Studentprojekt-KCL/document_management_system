"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

import argparse
from typing import Any
from collections.abc import Sequence

import requests
import uvicorn
from fastapi import FastAPI, Request, Query, HTTPException, Header
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dmis_logger import dms_warning, dms_info
from .auth import TokenVerifier
from initialisation_tools import read_env_variable, read_port


class API:
    """Management class for main API."""

    log_level: str | None = None
    search_api_url: str
    query_api_url: str
    token_verifier: TokenVerifier

    def __init__(
        self,
        search_api_url: str,
        query_api_url: str,
        keycloak_issuer: str,
        keycloak_jwks_url: str,
        keycloak_expected_azp: str,
        log_level: str | None = None,
    ) -> None:
        """Constructor."""
        self.app = FastAPI()

        self.log_level = log_level
        self.search_api_url = search_api_url.rstrip("/")
        self.query_api_url = query_api_url.rstrip("/")
        self.token_verifier = TokenVerifier(
            issuer=keycloak_issuer,
            jwks_url=keycloak_jwks_url,
            expected_azp=keycloak_expected_azp,
        )

        self.app.add_exception_handler(
            RequestValidationError,
            self.validation_exception_handler,
        )

        self.app.add_api_route("/search", self.search, methods=["GET"])
        self.app.add_api_route("/summary", self.summary, methods=["POST"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict[str, Any] = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"

        return JSONResponse(status_code=422, content=content)

    async def search(
        self,
        query: str = Query(..., min_length=1, max_length=200),
        authorization: str | None = Header(default=None),
    ) -> JSONResponse:
        """Forward search request to upstream search API, enrich results with classification, and return results."""
        claims = self.token_verifier.verify_access_token(authorization)
        dms_info(
            f"Authorized search request: "
            f"sub={claims.get('sub')} "
            f"user={claims.get('preferred_username')} "
            f"azp={claims.get('azp')}"
        )

        query = query.strip()
        if not query:
            dms_warning("Search request received empty query.")
            raise HTTPException(status_code=422)

        try:
            response = requests.get(  # noqa: ASYNC210 #Migration from requests will happen in separate commit.
                f"{self.search_api_url}/search",
                params={"query": query},
                timeout=120,
            )
            response.raise_for_status()
            search_data = response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Upstream search API returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc
        except requests.RequestException as exc:
            dms_warning(f"Search request to upstream API failed: {exc}")
            raise HTTPException(status_code=502) from exc

        if not isinstance(search_data, list):
            dms_warning("Search API returned unexpected JSON shape.")
            raise HTTPException(status_code=502)

        return JSONResponse(
            status_code=200,
            content={
                "results": search_data,
                "query": query,
            },
        )

    async def summary(
        self,
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ) -> JSONResponse:
        """Forward summary request to upstream summary API and return response."""
        claims = self.token_verifier.verify_access_token(authorization)
        dms_info(
            f"Authorized summary request: "
            f"sub={claims.get('sub')} "
            f"user={claims.get('preferred_username')} "
            f"azp={claims.get('azp')}"
        )

        file_pointer = body.get("file_pointer")
        if not isinstance(file_pointer, str):
            dms_info(f"Summary endpoint request expected 'file_pointer' to be string but got: {file_pointer!r}")
            raise HTTPException(status_code=422)

        try:
            response = requests.post(  # noqa: ASYNC210 #Migration from requests will happen in separate commit.
                f"{self.query_api_url}/summarize",
                json={"pointers": [file_pointer]},
                timeout=100,
            )
            response.raise_for_status()
            return response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Summary API returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc
        except requests.RequestException as exc:
            response_text = exc.response.text if exc.response is not None else ""
            dms_warning(f"Summary request to upstream API failed: {exc}. " f"Response body: {response_text}")
            raise HTTPException(status_code=502) from exc


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    bind_address = read_env_variable("API_BIND_ADDRESS")
    port = read_port("API_PORT")
    search_api_url = read_env_variable("DMIS_SEARCH_API_URL")
    query_api_url = read_env_variable("DMIS_QUERY_API_URL")
    keycloak_issuer = read_env_variable("KEYCLOAK_ISSUER")
    keycloak_jwks_url = read_env_variable("KEYCLOAK_JWKS_URL")
    keycloak_expected_azp = read_env_variable("KEYCLOAK_EXPECTED_AZP")

    log_level = "debug" if args.dev else None

    api = API(
        search_api_url=search_api_url,
        query_api_url=query_api_url,
        keycloak_issuer=keycloak_issuer,
        keycloak_jwks_url=keycloak_jwks_url,
        keycloak_expected_azp=keycloak_expected_azp,
        log_level=log_level,
    )

    uvicorn.run(
        api.app,
        host=bind_address,
        port=port,
        log_level=log_level,
    )
