from __future__ import annotations

from typing import Any

import aiohttp
from fastapi import HTTPException

from shared_functions.initialisation_tools import read_env_variable


class OidcConfig:
    def __init__(self) -> None:
        self.issuer_url = read_env_variable("DMISAPI_OIDC_ISSUER_URL").rstrip("/")
        self.client_id = read_env_variable("DMISAPI_OIDC_CLIENT_ID")
        self._metadata: dict[str, Any] | None = None

    async def get_metadata(self) -> dict[str, Any]:
        if self._metadata is not None:
            return self._metadata

        discovery_url = f"{self.issuer_url}/.well-known/openid-configuration"

        async with aiohttp.ClientSession() as session:
            async with session.get(discovery_url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=502, detail="Failed to load OIDC discovery document")

                metadata = await response.json()

        self._metadata = metadata
        return metadata

    async def token_endpoint(self) -> str:
        metadata = await self.get_metadata()
        return metadata["token_endpoint"]

    async def logout_endpoint(self) -> str | None:
        metadata = await self.get_metadata()
        return metadata.get("end_session_endpoint")

    async def jwks_uri(self) -> str:
        metadata = await self.get_metadata()
        return metadata["jwks_uri"]

    async def issuer(self) -> str:
        metadata = await self.get_metadata()
        return metadata["issuer"]