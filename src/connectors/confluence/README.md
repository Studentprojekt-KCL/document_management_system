The following should be exported in local environment (aligned with `dmis_environment_variable_naming`):

    CONFLUENCE_BIND_ADDR=<BIND_ADDRESS>               # e.g. 0.0.0.0 (default if unset)
    CONFLUENCE_BIND_PORT=<CONNECTOR_PORT>
    CONFLUENCE_SITE_URL=<CONFLUENCE_BASE_URL>       # e.g. https://tenant.atlassian.net

    CONFLUENCE_MAX_CONCURRENCY=<MAX_PARALLEL_CALLS> # optional, default 20

Optional fallback credentials (mainly for local scripts):

    CONFLUENCE_DEFAULT_EMAIL=<ATLASSIAN_EMAIL>
    CONFLUENCE_DEFAULT_API_TOKEN=<ATLASSIAN_API_TOKEN>

**Legacy names** (still honoured if the new names above are not set): ``CONFLUENCE_CONNECTOR_PORT``,
``CONFLUENCE_ADDRESS``, ``CONFLUENCE_EMAIL``, ``CONFLUENCE_API_TOKEN``.

## Authentication

Authentication is per request. Callers should supply:

    X-Confluence-Email: <user email>
    X-Confluence-Token: <user API token>

``GET /auth_user`` (same path as OAuth connectors) returns JSON only — no redirect. Example shape:

``type`` = ``api_token``, ``method`` = ``manual``, ``header_names``, ``labels``, ``help_url`` (for DMIS frontend).

The gateway still sends ``callback-url`` when proxying from other flows; this connector does not use it.

If headers are missing, endpoints return empty/no-op payloads and no Confluence API requests are made.

## Main endpoints

    GET  /index_needed_bool
    POST /get_files
    GET  /files_to_index
    GET  /stream_files_to_index
    GET  /connected_source_systems

Legacy endpoints also remain:

    GET /files
    GET /file
