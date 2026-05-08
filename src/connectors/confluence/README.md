The following should be exported in local environment:

    CONFLUENCE_CONNECTOR_PORT=<PORT>                             # connector HTTP listen port
    CONFLUENCE_ADDRESS=<CONFLUENCE_BASE_URL>                    # e.g. https://tenant.atlassian.net


## Authentication

Authentication is per request. Callers should supply:

    X-Confluence-Email: <user email>
    X-Confluence-Token: <user API token>

``GET /auth_user`` (same path as OAuth connectors) answers with **HTTP 200** and ``Content-Type:
application/json`` — no redirect. The gateway relays that JSON unchanged so the frontend receives a predictable contract.

Stable fields for UI (increment ``schema_version`` only on incompatible changes):

   ``schema_version``, ``connector``, ``flow``, ``required_headers``, ``steps``, ``summary``, ``oauth`` (with ``implemented_in_connector``).

Backward-compatible aliases remain: ``type``, ``method``, ``header_names``, ``labels``, ``help_url``.

OAuth 3LO references (not implemented): see ``oauth.documentation_url`` in the payload.

The gateway still sends ``callback-url`` when proxying; this connector does not use it.

If headers are missing, endpoints return empty/no-op payloads and no Confluence API requests are made.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/get_files` | POST | Batch fetch pages by pointer |
| `/stream_files_to_index` | POST | Stream NDJSON (subdata line + one page per line) |
| `/defined_fields` | GET | Lists field keys returned for indexed pages (gateway union) |
| `/auth_user` | GET | JSON auth contract for gateway/frontend |
