"""Methods for interacting with refresh service."""

import json
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

    async def send_post_request(
        self, end_point: str, params: dict | None = None, headers: dict | None = None, body: dict | list | None = None
    ) -> list | dict:
        """Send POST request to refresh service."""
        try:
            response = await self.http_client.post(
                f"{self.service_url.rstrip('/')}/{end_point.lstrip('/')}",
                params=params,
                headers=headers,
                json=body,
                timeout=self.timeout,
            )
            return response.json()
        except json.JSONDecodeError:
            dms_warning("Unauthorized request to request service.")
        except httpx.TimeoutException:
            dms_warning("Request timed out")
        except httpx.HTTPError:
            dms_warning("Failed to connect to connector.")
        return {}
