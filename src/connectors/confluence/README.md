The following should be exported in local environment:

    CONFLUENCE_CONNECTOR_PORT=<PORT>                             # connector HTTP listen port
    CONFLUENCE_ADDRESS=<CONFLUENCE_BASE_URL>                    # e.g. https://tenant.atlassian.net


## Authentication

Authentication is per request. Callers should supply:

    X-Confluence-Email: <user email>
    X-Confluence-Token: <user API token>

If headers are missing, endpoints return empty/no-op payloads and no Confluence API requests are made.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/get_files` | POST | Batch fetch pages by pointer |
| `/stream_files_to_index` | POST | Stream NDJSON (subdata line + one page per line) |
| `/defined_fields` | GET | Lists field keys returned for indexed pages (gateway union) |
