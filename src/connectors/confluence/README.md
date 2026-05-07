The following should be exported in local environment:

    CONCONFLUENCE_BIND_PORT=<BIND_PORT>
    CONCONFLUENCE_BIND_ADDR=<BIND_ADDR>
    CONCONFLUENCE_CONFLUENCE_URL=<CONFLUENCE_BASE_URL>          # e.g. https://tenant.atlassian.net


## Authentication

Authentication is per request. Callers should supply:

    X-Confluence-Email: <user email>
    X-Confluence-Token: <user API token>

If headers are missing, endpoints return empty/no-op payloads and no Confluence API requests are made.
