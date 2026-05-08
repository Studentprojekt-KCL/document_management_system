"""Methods for interacting with refresh service."""

import httpx

from shared_functions.dmis_logger import dms_warning


class RefreshServiceClient:
    """
    Class for interacing with connectors to source systems
    """

    timeout: int
    http_client: httpx.AsyncClient

    def __init__(self, service_url: str, timeout: int) -> None:
        self.service_url = service_url
        self.timeout = timeout
        self.http_client = httpx.AsyncClient()

    async def send_request(
        self, end_point: str, params: dict | None = None, headers: dict | None = None, body: dict | None = None
    ) -> list | dict:
        """Send request to refresh service."""
        try:
            await self.http_client.post(
                f"{self.service_url}{end_point}", params=params, headers=headers, json=body, timeout=self.timeout
            )
        except httpx.TimeoutException:
            dms_warning("Request timed out")
        except httpx.HTTPError:
            dms_warning("Failed to connect to connector.")
        return []
