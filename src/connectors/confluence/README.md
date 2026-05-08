The following should be exported in local environment:

    CONFLUENCE_CONNECTOR_PORT=<CONNECTOR_PORT>
    CONFLUENCE_ADDRESS=<CONFLUENCE_BASE_URL>          # e.g. https://tenant.atlassian.net
    CONFLUENCE_MAX_CONCURRENCY=<MAX_PARALLEL_CALLS>   # optional, default 20

Optional fallback credentials (mainly for local scripts):

    CONFLUENCE_EMAIL=<ATLASSIAN_EMAIL>
    CONFLUENCE_API_TOKEN=<ATLASSIAN_API_TOKEN>

## Authentication

Authentication is per request. Callers should supply:

    X-Confluence-Email: <user email>
    X-Confluence-Token: <user API token>

``GET /auth_user`` (same path as OAuth connectors) answers with **HTTP 200** and ``Content-Type:
application/json`` — no redirect. The gateway relays that JSON unchanged so the frontend receives a predictable contract.

Stable fields for UI (increment ``schema_version`` only on incompatible changes):

   ``schema_version``, ``connector``, ``flow``, ``required_headers``, ``steps``, ``summary``, ``oauth`` (with ``implemented_in_connector``).

Backward-compatible aliases remain: ``type``, ``method``, ``header_names``, ``labels``, ``help_url``.

OAuth 3LO references (not implemented): see ``oauth.documentation_url`` in the payload and note in PR #520 discussion.

The gateway still sends ``callback-url`` when proxying; this connector does not use it.

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
