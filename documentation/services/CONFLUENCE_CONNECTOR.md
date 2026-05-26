# Confluence Connector

Communicates with the Atlassian Confluence Cloud REST API (v2) and manages delivery of Confluence pages as indexable documents.

## Configuration

### Environment Variables

- **CONCONFLUENCE_BIND_ADDR**: Which address to bind to.
- **CONCONFLUENCE_BIND_PORT**: Which port to bind to.
- **CONCONFLUENCE_SYSTEM_NAME**: Source system identifier, visible in the frontend.
- **CONCONFLUENCE_CONFLUENCE_URL**: Confluence site base URL, used for clickable links (e.g. `https://yourcompany.atlassian.net`).
- **CONCONFLUENCE_CLOUD_ID**: Atlassian cloud ID for the target site. The `id` field from `GET https://api.atlassian.com/oauth/token/accessible-resources` after a successful OAuth login.
- **CONCONFLUENCE_CONNECT_SERVICE_CALLBACK**: Public URL of the connector's `/callback` endpoint, registered as the OAuth app's callback URL.

OAuth (required for `/auth_user`, `/callback`, `/refresh_token`, and `/validate_token`):

- **CONCONFLUENCE_CLIENT_ID**: OAuth 2.0 client ID from the Atlassian developer console.
- **CONCONFLUENCE_CLIENT_SECRET**: OAuth 2.0 client secret.
- **CONCONFLUENCE_STATE_SIGNING_SECRET**: Random HMAC secret used to sign and validate CSRF state tokens.
- **CONCONFLUENCE_AUTH_URL**: Atlassian authorization endpoint (default: `https://auth.atlassian.com/authorize`).
- **CONCONFLUENCE_TOKEN_URL**: Atlassian token endpoint (default: `https://auth.atlassian.com/oauth/token`).
- **CONCONFLUENCE_SCOPES**: OAuth scopes to request (e.g. `read:space:confluence read:page:confluence offline_access`).
- **CONCONFLUENDE_CHECK_AUTH_URL**: URL used by `/validate_token` to verify an access token (e.g. `https://api.atlassian.com/oauth/token/accessible-resources`).

### Flags

- `--dev`: Enable dev prints.

## Behaviour

The connector operates in two modes:

**Incremental indexing** (`/stream_files_to_index`):

All Confluence spaces accessible to the authenticated user are discovered via the REST API v2 `/spaces` endpoint. For each space, pages are fetched in batches of up to 200 via the `/pages` endpoint. The `subdata` field carries a URL-safe base64-encoded JSON object mapping each space key to the ISO timestamp of the latest page version seen in that space during the previous successful index run (e.g. `{ "TEAM": "2024-06-01T12:00:00.000Z" }`). Only pages whose `version.createdAt` is newer than the stored checkpoint for their space are included in the next run.

Page bodies are fetched with `body-format=storage`. HTML tags are stripped and the remaining plain text is base64-encoded in the `content` field. Up to 20 page fetches run concurrently. The response is a stream of NDJSON lines: the first line carries the updated `subdata` header; each subsequent line is one page record.

When `subdata` is omitted or invalid, all accessible pages in all spaces are indexed.

**File retrieval** (`/get_files`):

Pages are fetched individually by pointer URL from the Confluence REST API. Content and last-edit date are included only when the corresponding request parameters are set.

**Authentication**:

All file-serving endpoints read the user's Atlassian OAuth access token from the `X-Confluence-Token` header. If the header is absent, the endpoint returns an empty result and no Confluence API requests are made. Tokens are obtained through the OAuth 2.0 authorization-code flow exposed by the connector: `/auth_user` → Atlassian consent page → `/callback` → tokens. Refresh tokens can be exchanged via `/refresh_token`.

## Deployment

### Docker

The connector is packaged as a Docker image built from `src/connectors/confluence/Dockerfile`. Add a service entry to your `docker-compose.yaml` with all required environment variables:

```yaml
connector-confluence:
  image: connector-confluence:latest
  container_name: connector-confluence
  restart: always
  environment:
    CONCONFLUENCE_BIND_ADDR: ${CONCONFLUENCE_BIND_ADDR}
    CONCONFLUENCE_BIND_PORT: ${CONCONFLUENCE_BIND_PORT}
    CONCONFLUENCE_SYSTEM_NAME: ${CONCONFLUENCE_SYSTEM_NAME}
    CONCONFLUENCE_CONFLUENCE_URL: ${CONCONFLUENCE_CONFLUENCE_URL}
    CONCONFLUENCE_CLOUD_ID: ${CONCONFLUENCE_CLOUD_ID}
    CONCONFLUENCE_CLIENT_ID: ${CONCONFLUENCE_CLIENT_ID}
    CONCONFLUENCE_CLIENT_SECRET: ${CONCONFLUENCE_CLIENT_SECRET}
    CONCONFLUENCE_STATE_SIGNING_SECRET: ${CONCONFLUENCE_STATE_SIGNING_SECRET}
    CONCONFLUENCE_AUTH_URL: ${CONCONFLUENCE_AUTH_URL}
    CONCONFLUENCE_TOKEN_URL: ${CONCONFLUENCE_TOKEN_URL}
    CONCONFLUENCE_SCOPES: ${CONCONFLUENCE_SCOPES}
    CONCONFLUENCE_CONNECT_SERVICE_CALLBACK: ${CONCONFLUENCE_CONNECT_SERVICE_CALLBACK}
    CONCONFLUENDE_CHECK_AUTH_URL: ${CONCONFLUENDE_CHECK_AUTH_URL}
```

Build the image:

```
docker compose build connector-confluence
```

### Atlassian OAuth App Setup

The connector requires an OAuth 2.0 app registered in the Atlassian developer console. See [SETUP_INSTRUCTIONS.md](../SETUP_INSTRUCTIONS.md#confluence) for step-by-step instructions on creating the app, configuring the callback URL, granting the required API permissions, and setting the required environment variables.

After the first OAuth login, retrieve the site cloud ID from `GET https://api.atlassian.com/oauth/token/accessible-resources` and set `CONCONFLUENCE_CLOUD_ID` to the `id` of the target Confluence site.

### Local Development

Set the required environment variables, then run:

```
pip install -e src/connectors/confluence
confluence_connector --dev
```

The `--dev` flag enables verbose debug logging.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/auth_user` | GET | Start OAuth flow. Returns a redirect URL to the Atlassian consent page. |
| `/callback` | GET | OAuth callback. Validates the state token and exchanges the authorization code for access and refresh tokens. |
| `/refresh_token` | GET | Exchange a refresh token for a new access token. |
| `/validate_token` | GET | Check whether a token is valid. |
| `/defined_fields` | GET | List all field keys returned for indexed documents. |
| `/get_files` | POST | Fetch specific pages by pointer URL. |
| `/stream_files_to_index` | POST | Stream NDJSON of all new or changed pages. |

### Auth User

Start the OAuth 2.0 authorization-code flow. Returns a redirect URL the client should open in a browser.

*Response*

```json
{
    "redirect": <STRING>
}
```

### Callback

Validate the state token returned by Atlassian and exchange the authorization code for an access and refresh token pair.

*Params*

- **code**: Authorization code returned by Atlassian.
- **state**: Signed state token for CSRF validation.

*Response*

```json
{
    "access_token": <STRING>,
    "expires_in": <INTEGER>,
    "refresh_token": <STRING>,
    "token_type": <STRING>,
    "scope": <STRING>
}
```

### Refresh Token

Exchange a refresh token for a new access token.

*Headers*

- **refresh-token**: The refresh token to exchange.

*Response*

```json
{
    "access_token": <STRING>,
    "expires_in": <INTEGER>,
    "refresh_token": <STRING>,
    "token_type": <STRING>,
    "scope": <STRING>
}
```

### Validate Token

Check whether the provided token is accepted by the Confluence API.

*Headers*

- **X-Confluence-Token**: Atlassian OAuth access token to validate.

*Response*

```json
{
    "valid": <BOOLEAN>
}
```

### Defined Fields

Fetch all field keys that may be present in an indexed page object.

*Response*

```json
[
    <STRING>,
    <STRING>,
    <STRING>
]
```

### Get Files

Fetch a specified list of pages by pointer URL.

*Headers*

- **X-Confluence-Token**: Atlassian OAuth access token.

*Params*

- **include_content**: Include page content (boolean).
- **include_last_edit_date**: Include the date of the last page version (boolean).

*Body*

```json
{
    "file_pointers": [
        <STRING>,
        <STRING>,
        <STRING>
    ]
}
```

*Response*

`last_edit_date` is only present when `include_last_edit_date=True` (the default). `content` is always present; its value is `null` when `include_content=False`.

```json
[
    {
        "unique_pointer": <STRING>,
        "name": <STRING>,
        "size": <INTEGER>,
        "last_edit_date": <STRING>,
        "type": <STRING>,
        "source_system": <STRING>,
        "clickable_url": <STRING>,
        "file_type": <STRING>,
        "file_type_description": <STRING>,
        "content": <STRING>
    }
]
```

### Stream Files to Index

Stream all pages the requesting user has access to that have been added or changed since the last index run.

*Headers*

- **X-Confluence-Token**: Atlassian OAuth access token.

*Body*

```json
{
    "subdata": <STRING>
}
```

*Response*

Note: sent as a stream of NDJSON lines.

```json
{"subdata": <STRING>}
{
    "unique_pointer": <STRING>,
    "name": <STRING>,
    "size": <INTEGER>,
    "type": <STRING>,
    "source_system": <STRING>,
    "last_edit_date": <STRING>,
    "clickable_url": <STRING>,
    "file_type": <STRING>,
    "file_type_description": <STRING>,
    "content": <STRING>
}
```
