The following should be exported in local environment:

    CONFLUENCE_CONNECTOR_PORT=<PORT>                             # connector HTTP listen port
    CONFLUENCE_ADDRESS=<CONFLUENCE_BASE_URL>                    # e.g. https://tenant.atlassian.net

Optional script-style credentials when not using HTTP headers:

    CONFLUENCE_DEFAULT_EMAIL=<ATLASSIAN_EMAIL>
    CONFLUENCE_DEFAULT_API_TOKEN=<ATLASSIAN_API_TOKEN>

Legacy names also accepted as fallbacks:

    ``CONFLUENCE_EMAIL``, ``CONFLUENCE_API_TOKEN``

## Authentication

Authentication is per request. Callers should supply:

    X-Confluence-Email: <user email>
    X-Confluence-Token: <user API token>

``GET /auth_user`` returns JSON describing how to authenticate (schema for the DMIS frontend; no OAuth redirect on this connector). See response fields ``schema_version``, ``flow``, ``required_headers``, and legacy keys ``type`` / ``method`` / ``header_names``.

If headers are missing, endpoints return empty/no-op payloads and no Confluence API requests are made.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/get_files` | POST | Batch fetch pages by pointer |
| `/stream_files_to_index` | POST | Stream NDJSON (subdata line + one page per line) |
| `/defined_fields` | GET | Lists field keys returned for indexed pages (gateway union) |
| `/auth_user` | GET | JSON auth contract for gateway/frontend |
