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
