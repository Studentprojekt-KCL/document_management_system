# SharePoint Connector

Communicates with the Microsoft Graph API and manages file delivery from SharePoint document libraries.

## Configuration

### Environment Variables

- **CONSHAREPOINT_BIND_ADDR**: Which address to bind to.
- **CONSHAREPOINT_BIND_PORT**: Which port to bind to.
- **CONSHAREPOINT_GRAPH_BASE**: Microsoft Graph API base URL (e.g. `https://graph.microsoft.com/v1.0`). Must not have a trailing slash.
- **CONSHAREPOINT_SYSTEM_NAME**: Source system identifier, visible in the frontend.
- **CONSHAREPOINT_TENANT_ID**: Azure AD tenant ID. Found in the Azure portal under Entra ID > Overview.
- **CONSHAREPOINT_CLIENT_ID**: Client ID of the application registered in Azure AD.
- **CONSHAREPOINT_CLIENT_SECRET**: Client secret of the application registered in Azure AD.
- **CONSHAREPOINT_STATE_SIGNING_SECRET**: Random HMAC secret used to sign and validate CSRF state tokens.
- **CONSHAREPOINT_CONNECT_SERVICE_CALLBACK**: Public URL of the connector's `/callback` endpoint, registered as the app's redirect URI in Azure AD.

### Flags

- `--dev`: Enable dev prints.

## Behaviour

The connector operates in two modes:

**Incremental indexing** (`/stream_files_to_index`):

All SharePoint sites accessible to the authenticated user are discovered by querying the Microsoft Search API in pages of 500. Document library drives are then fetched for each site in parallel. A paginated delta query runs for every drive (up to 20 concurrent requests, enforced by a semaphore). Folders and deletion tombstones returned by delta queries are filtered out; only file items are indexed.

The optional `subdata` query parameter carries a gzip-compressed, URL-safe base64-encoded JSON object mapping each drive ID to the delta token returned by its previous sync. When provided, each drive's delta query resumes from that token and only changed files are returned. When omitted, a full scan is performed. After all delta queries complete, file content is fetched for every record in parallel (null on failure). The first NDJSON line is the updated `subdata` header; each subsequent line is one file record.

Rate-limited responses (HTTP 429) are retried up to three times with the `Retry-After` delay from the response header.

**File retrieval** (`/get_files`):

File metadata is fetched from the Graph API per pointer URL. Content and last-edit date are fetched only when the corresponding request parameters are set.

**Authentication**:

All endpoints read the user's Microsoft OAuth token from the `X-SharePoint-Token` header. Tokens are obtained through the OAuth 2.0 authorization-code flow: `/auth_user` redirects the user to Microsoft login, and `/callback` exchanges the returned code for access and refresh tokens. Access tokens are valid for one hour; `/refresh_token` exchanges a stored refresh token for a new token pair.

## Deployment

### Docker

The connector is packaged as a Docker image built from `src/connectors/sharepoint/Dockerfile`. Add a service entry to your `docker-compose.yaml`:

```yaml
connector-sharepoint:
  image: connector-sharepoint:latest
  container_name: connector-sharepoint
  restart: always
  environment:
    CONSHAREPOINT_BIND_ADDR: ${CONSHAREPOINT_BIND_ADDR}
    CONSHAREPOINT_BIND_PORT: ${CONSHAREPOINT_BIND_PORT}
    CONSHAREPOINT_GRAPH_BASE: ${CONSHAREPOINT_GRAPH_BASE}
    CONSHAREPOINT_SYSTEM_NAME: ${CONSHAREPOINT_SYSTEM_NAME}
    CONSHAREPOINT_TENANT_ID: ${CONSHAREPOINT_TENANT_ID}
    CONSHAREPOINT_CLIENT_ID: ${CONSHAREPOINT_CLIENT_ID}
    CONSHAREPOINT_CLIENT_SECRET: ${CONSHAREPOINT_CLIENT_SECRET}
    CONSHAREPOINT_STATE_SIGNING_SECRET: ${CONSHAREPOINT_STATE_SIGNING_SECRET}
    CONSHAREPOINT_CONNECT_SERVICE_CALLBACK: ${CONSHAREPOINT_CONNECT_SERVICE_CALLBACK}
```

Build the image:

```
docker compose build connector-sharepoint
```

### Azure AD App Registration

The connector requires an application registered in Azure AD. See [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md#sharepoint) for step-by-step instructions on registering the app, granting the required permissions, and setting the required environment variables.

### Local Development

Set the required environment variables, then run:

```
pip install -e src/connectors/sharepoint
sharepoint_connector --dev
```

The `--dev` flag enables verbose debug logging.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/auth_user` | GET | Start OAuth flow. Returns a redirect URL to the Microsoft login page. |
| `/callback` | GET | OAuth callback. Validates the state token and exchanges the authorization code for access and refresh tokens. |
| `/refresh_token` | GET | Exchange a refresh token for a new access token. |
| `/get_files` | POST | Fetch specific files by pointer URL. |
| `/stream_files_to_index` | GET | Stream NDJSON of all new or changed files. |

### Auth User

Start the OAuth 2.0 authorization-code flow. Returns a redirect URL the client should open in a browser.

*Response*

```json
{
    "redirect": <STRING>
}
```

### Callback

Validate the state token returned by Microsoft and exchange the authorization code for an access and refresh token pair.

*Params*

- **code**: Authorization code returned by Microsoft.
- **state**: Signed state token for CSRF validation.

*Response*

```json
{
    "access_token": <STRING>,
    "refresh_token": <STRING>,
    "expires_in": <INTEGER>,
    "token_type": <STRING>
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
    "refresh_token": <STRING>,
    "expires_in": <INTEGER>,
    "token_type": <STRING>
}
```

### Get Files

Fetch a specified list of files by pointer URL.

*Headers*

- **X-SharePoint-Token**: Microsoft OAuth access token.

*Params*

- **include_content**: Include file content (boolean).
- **include_last_edit_date**: Include the date of the last modification (boolean).

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

```json
[
    {
        "unique_pointer": <STRING>,
        "name": <STRING>,
        "size": <INTEGER>,
        "type": <STRING>,
        "source_system": <STRING>,
        "clickable_url": <STRING>,
        "file_type": <STRING>,
        "file_type_description": <STRING>,
        "last_edit_date": <STRING>,
        "content": <STRING>
    }
]
```

### Stream Files to Index

Stream all files the requesting user has access to that have been added or changed since the last index run.

*Headers*

- **X-SharePoint-Token**: Microsoft OAuth access token.

*Params*

- **subdata**: Gzip-compressed, URL-safe base64-encoded JSON mapping drive IDs to delta tokens from the previous run (optional). Omit to perform a full scan.

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
