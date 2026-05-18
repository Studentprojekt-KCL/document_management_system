from __future__ import annotations

from typing import Any

import aiohttp
from fastapi import HTTPException

from shared_functions.initialisation_tools import read_env_variable


class OidcConfig:
    
    _session: aiohttp.ClientSession | None

    def __init__(self) -> None:
        self.issuer_url = read_env_variable("DMISAPI_AD_URL").rstrip("/")
        self.client_id = read_env_variable("DMISAPI_AD_CLIENT_ID")
        self._metadata: dict[str, Any] | None = None
        self._session = None

    async def close_session(self) -> None:
        """Close aiohttp session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def get_session(self) -> aiohttp.ClientSession:
        """Return cached aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        return self._session
    
    async def close_session(self) -> None:
        """Tear down sessions."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

        await self.oidc.close_session()

    async def get_metadata(self) -> dict[str, Any]:
        """Fetch OIDC metadata."""
        if self._metadata is not None:
            return self._metadata

        discovery_url = f"{self.issuer_url}/.well-known/openid-configuration"

        session = await self.get_session()

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