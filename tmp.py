from typing import Any, Annotated
import argparse
import secrets
import time
from urllib.parse import urlencode
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder


async def callback(self, request: Request, code: str | None = None) -> JSONResponse:
    """Callback endpoint to set in GitLab application."""
    signed_state = request.query_params.get("state")
    if signed_state is None:
        return JSONResponse(content="ERROR", status_code=403)

    validation_status, _ = validate_decode_state(signed_state, self.state_secret)
    if validation_status is False:
        return JSONResponse(content="ERROR", status_code=403)

    token_url = f"{self.gitlab_url}/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": str(request.url_for("callback")),
        "client_id": self.gitlab_client_id,
        "client_secret": self.gitlab_client_secret,
    }
    token_json = await self.gitlab_instance.execute_post_request(token_url, data=data)

    if not token_json.get("access_token"):
        return JSONResponse(content="ERROR", status_code=400)

    return JSONResponse(content=token_json, status_code=200)