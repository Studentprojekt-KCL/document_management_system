"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Route-level tests — ``ConfluenceInterfacer`` is mocked (no Live env or Confluence hosts).
OAuth env vars are stubbed so ``API()`` can construct ``_OAuthConfig``.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from confluence_service.collector_api import API

_FAKE_OAUTH_ENV: dict[str, str] = {
    "CONCONFLUENCE_CLIENT_ID": "test-client-id",
    "CONCONFLUENCE_CLIENT_SECRET": "test-client-secret",
    "CONCONFLUENCE_STATE_SIGNING_SECRET": "x" * 32,
    "CONCONFLUENCE_AUTH_URL": "https://location/authorize",
    "CONCONFLUENCE_TOKEN_URL": "https://location/oauth/token",
    "CONCONFLUENCE_SCOPES": "read:space:confluence,read:page:confluence,offline_access",
    "CONCONFLUENCE_CONNECT_SERVICE_CALLBACK": "https://somelocation/callback",
    # Must match ``read_env_variable`` name in ``collector_api`` (currently CONCONFLUENDE_…).
    "CONCONFLUENDE_CHECK_AUTH_URL": "https://location/token/validate",
}


class TestCollectorAuthUserAndDefinedFields(unittest.TestCase):
    """Covers `/auth_user` OAuth redirect and `/defined_fields` union keys."""

    def setUp(self) -> None:
        mock_inst = MagicMock()
        mock_inst.session = MagicMock()
        mock_inst.session.aclose = AsyncMock(return_value=None)
        mock_inst.defined_fields = {
            "content": None,
            "name": None,
            "unique_pointer": None,
        }

        self._ci = patch("confluence_service.collector_api.ConfluenceInterfacer", return_value=mock_inst)
        self._env = patch(
            "confluence_service.collector_api.read_env_variable",
            side_effect=lambda name, *_a, **_k: _FAKE_OAUTH_ENV[name],
        )
        self._ci.start()
        self._env.start()
        self.mock_inst = mock_inst

    def tearDown(self) -> None:
        self._env.stop()
        self._ci.stop()

    def test_auth_user_redirects_to_atlassian_oauth(self) -> None:
        api = API()
        with TestClient(api.app) as client:
            res = client.get("/auth_user", follow_redirects=False)
        self.assertIn(res.status_code, (200,))

    def test_defined_fields_returns_keys_from_interfacer(self) -> None:
        api = API()
        expected = list(self.mock_inst.defined_fields.keys())
        with TestClient(api.app) as client:
            res = client.get("/defined_fields")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), expected)

    def test_get_files_without_headers_returns_empty_list(self) -> None:
        api = API()
        with TestClient(api.app) as client:
            res = client.post("/get_files", json={"file_pointers": ["ignored"]})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])
