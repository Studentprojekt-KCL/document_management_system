The following should be exported in local environment:

    CONCONFLUENCE_BIND_PORT=<BIND_PORT>
    CONCONFLUENCE_BIND_ADDR=<BIND_ADDR>
    CONCONFLUENCE_SYSTEM_NAME=<DISPLAY_NAME>                    # e.g. Confluence
    CONCONFLUENCE_CONFLUENCE_URL=<CONFLUENCE_BASE_URL>          # e.g. https://yourcompany.atlassian.net (used for clickable links)
    CONCONFLUENCE_CLOUD_ID=<SITE_CLOUD_ID>                      # the `id` field from GET https://api.atlassian.com/oauth/token/accessible-resources

    # OAuth 2.0 (3LO) — obtain from developer.atlassian.com
    CONCONFLUENCE_CLIENT_ID=<ATLASSIAN_OAUTH_CLIENT_ID>
    CONCONFLUENCE_CLIENT_SECRET=<ATLASSIAN_OAUTH_CLIENT_SECRET>
    CONCONFLUENCE_STATE_SIGNING_SECRET=<RANDOM_SECRET>          # used to sign CSRF state param

    # Atlassian endpoint URLs (values below are correct for all Atlassian Cloud tenants)
    CONCONFLUENCE_AUTH_URL=https://auth.atlassian.com/authorize
    CONCONFLUENCE_TOKEN_URL=https://auth.atlassian.com/oauth/token

    #OAuth scopes to request
    CONCONFLUENCE_SCOPES=read:space:confluence read:page:confluence offline_access
    CONCONFLUENCE_CONNECT_SERVICE_CALLBACK:callback for token


## Atlassian developer console setup

1. Go to [developer.atlassian.com](https://developer.atlassian.com) and create an **OAuth 2.0 (3LO)** app.
2. Set the **Callback URL** to the connector's public `/callback` endpoint (e.g. `https://your-connector-host/callback`).
3. Enable API permissions matching `CONCONFLUENCE_SCOPES`: `read:space:confluence`, `read:page:confluence`, `offline_access`.
4. Copy the **Client ID** → `CONCONFLUENCE_CLIENT_ID` and **Client Secret** → `CONCONFLUENCE_CLIENT_SECRET`.


## Authentication

Authentication uses OAuth 2.0. Supply the Bearer access token obtained via the `/auth_user` → `/callback` flow:

    X-Confluence-Token: <OAuth access token>

If the header is missing, endpoints return empty/no-op payloads and no Confluence API requests are made.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/auth_user` | GET | Redirects user to Atlassian OAuth login |
| `/callback` | GET | Exchanges authorization code for access + refresh tokens |
| `/refresh_token` | GET | Refreshes an access token (pass `refresh-token` header) |
| `/get_files` | POST | Batch fetch pages by pointer |
| `/stream_files_to_index` | POST | Stream NDJSON (subdata line + one page per line) |
| `/defined_fields` | GET | Lists field keys returned for indexed pages (gateway union) |
