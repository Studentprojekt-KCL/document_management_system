The following should be exported in local environment (DMIS naming: ``CONCONFLUENCE_*``):

    CONCONFLUENCE_BIND_ADDR=<BIND_ADDRESS>                     # default 0.0.0.0 in Docker
    CONCONFLUENCE_BIND_PORT=<BIND_PORT>
    CONCONFLUENCE_CONFLUENCE_URL=<CONFLUENCE_BASE_URL>         # e.g. https://tenant.atlassian.net

Optional script-style credentials when not using HTTP headers:

    CONFLUENCE_EMAIL=<ATLASSIAN_EMAIL>
    CONFLUENCE_API_TOKEN=<ATLASSIAN_API_TOKEN>

**Legacy URL names** also read when ``CONCONFLUENCE_CONFLUENCE_URL`` is unset:
``CONFLUENCE_SITE_URL``, ``CONFLUENCE_ADDRESS``. Optional newer aliases:
``CONFLUENCE_DEFAULT_EMAIL`` / ``CONFLUENCE_DEFAULT_API_TOKEN``.

## Authentication

Authentication is per request. Callers should supply:

    X-Confluence-Email: <user email>
    X-Confluence-Token: <user API token>

``GET /auth_user`` returns JSON describing manual token auth (``type`` / ``method`` / ``header_names`` / ``labels`` / ``help_url``). There is no OAuth redirect on this connector.

If headers are missing, endpoints return empty/no-op payloads and no Confluence API requests are made.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/get_files` | POST | Batch fetch pages by pointer |
| `/stream_files_to_index` | POST | Stream NDJSON (subdata line + one page per line) |
| `/auth_user` | GET | JSON auth contract for frontend (#478) |
