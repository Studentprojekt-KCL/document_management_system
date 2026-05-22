# GitHub Connector

Communicates with the GitHub REST API and manages file delivery from repositories.

## Configuration

### Environment Variables

- **CONGITHUB_BIND_ADDR**: Which address to bind to.
- **CONGITHUB_BIND_PORT**: Which port to bind to.
- **CONGITHUB_GITHUB_API_URL**: GitHub REST API base URL. For github.com: `https://api.github.com`. For GitHub Enterprise: `https://<host>/api/v3/`.
- **CONGITHUB_GITHUB_BASE_URL**: GitHub web root, used for OAuth redirects. For github.com: `https://github.com`. For GitHub Enterprise: `https://<host>`.
- **CONGITHUB_GITHUB_SYSTEM_NAME**: Source system identifier, visible in the frontend.
- **CONGITHUB_GITHUB_API_VERSION**: GitHub API version header (e.g. `2022-11-28`).
- **CONGITHUB_CONNECT_SERVICE_CALLBACK**: Public URL of the connector's `/callback` endpoint, registered as the GitHub App callback URL.

OAuth (required for `/auth_user`, `/callback`, and `/refresh_token`):

- **CONGITHUB_CLIENT_ID**: GitHub App client ID.
- **CONGITHUB_CLIENT_SECRET**: GitHub App client secret.
- **CONGITHUB_STATE_SIGNING_SECRET**: Random HMAC secret used to sign and validate CSRF state tokens.

Optional:

- **CONGITHUB_GITHUB_ORG**: Organization login slug (the URL slug in `github.com/<org-login>`). When set, the connector indexes that organization's repositories instead of the authenticated user's repositories. The GitHub App must be installed on the organization.
- **CONGITHUB_GITHUB_EXCLUDE_PATHS**: Comma-separated list of path substrings. Files whose paths contain any of these tokens are excluded from indexing.

### Flags

- `--dev`: Enable dev prints.

## Behaviour

The connector operates in two modes:

**Incremental indexing** (`/stream_files_to_index`):

Repositories are fetched from the GitHub API in pages of 100, ordered by push time. The `subdata` field (a base64-encoded JSON object) carries a per-repo map of `{ "owner/repo": "<pushed_at ISO timestamp>" }` from the previous successful index run. Only repositories whose current `pushed_at` is newer than the stored snapshot are re-archived, keeping traffic low for large installations.

Archives (zipballs) are downloaded with 10 concurrent workers and unpacked with a further 10 concurrent unzip workers to avoid blocking the event loop. Excluded paths (`CONGITHUB_GITHUB_EXCLUDE_PATHS`) are filtered during unpack. The response is a stream of NDJSON lines: the first line carries the updated `subdata` header; each subsequent line is one file.

Legacy `subdata` (a single ISO datetime string instead of a JSON object) is treated as a global "only index pushes after this time" floor and is automatically migrated to the per-repo format on the next run.

**File retrieval** (`/get_files`):

Pointer URLs are parsed to extract the repository full name, file path, and branch ref. The file is fetched from the GitHub contents API. When `include_last_edit_date` is requested, the last-commit date for that path is fetched separately.

**Authentication**:

All file-serving endpoints read the user's GitHub OAuth token from the `X-GitHub-Token` header. If the header is absent, the endpoint returns an empty result. Tokens are obtained through the OAuth flow exposed by the connector: `/auth_user` → GitHub consent page → `/callback` → tokens. GitHub App access tokens are valid for 8 hours; refresh tokens are valid for 6 months and can be exchanged via `/refresh_token`.

## Deployment

### Docker

The connector is packaged as a Docker image built from `src/connectors/github/Dockerfile`. Add a service entry to your `docker-compose.yaml` with all required environment variables:

```yaml
connector-github:
  image: connector-github:latest
  container_name: connector-github
  restart: always
  environment:
    CONGITHUB_BIND_ADDR: ${CONGITHUB_BIND_ADDR}
    CONGITHUB_BIND_PORT: ${CONGITHUB_BIND_PORT}
    CONGITHUB_GITHUB_API_URL: ${CONGITHUB_GITHUB_API_URL}
    CONGITHUB_GITHUB_BASE_URL: ${CONGITHUB_GITHUB_BASE_URL}
    CONGITHUB_GITHUB_SYSTEM_NAME: ${CONGITHUB_GITHUB_SYSTEM_NAME}
    CONGITHUB_GITHUB_API_VERSION: ${CONGITHUB_GITHUB_API_VERSION}
    CONGITHUB_CONNECT_SERVICE_CALLBACK: ${CONGITHUB_CONNECT_SERVICE_CALLBACK}
    CONGITHUB_CLIENT_ID: ${CONGITHUB_CLIENT_ID}
    CONGITHUB_CLIENT_SECRET: ${CONGITHUB_CLIENT_SECRET}
    CONGITHUB_STATE_SIGNING_SECRET: ${CONGITHUB_STATE_SIGNING_SECRET}
```

Build the image:

```
docker compose build connector-github
```

### GitHub App Setup

The connector requires a GitHub App registered with the target account or organization. See [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md#github) for step-by-step instructions on creating the app, retrieving credentials, installing it on the target organization, and setting the required environment variables.

### Local Development

Set the required environment variables, then run:

```
pip install -e src/connectors/github
github_connector --dev
```

The `--dev` flag enables verbose debug logging.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/auth_user` | GET | Start OAuth flow. Returns a redirect URL to the GitHub consent page. |
| `/callback` | GET | OAuth callback. Validates the state token and exchanges the authorization code for access and refresh tokens. |
| `/refresh_token` | GET | Exchange a refresh token for a new access token. |
| `/validate_token` | GET | Check whether a token is valid. |
| `/defined_fields` | GET | List all field keys returned for indexed documents. |
| `/get_files` | POST | Fetch specific files by pointer URL. |
| `/stream_files_to_index` | POST | Stream NDJSON of all new or changed files. |

### Auth User

Start the OAuth2 authorization-code flow. Returns a redirect URL the client should open in a browser.

*Response*

```json
{
    "redirect": <STRING>
}
```

### Callback

Validate the state token returned by GitHub and exchange the authorization code for an access and refresh token pair.

*Params*

- **code**: Authorization code returned by GitHub.
- **state**: Signed state token for CSRF validation.

*Response*

```json
{
    "access_token": <STRING>,
    "expires_in": <INTEGER>,
    "refresh_token": <STRING>,
    "refresh_token_expires_in": <INTEGER>,
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
    "refresh_token_expires_in": <INTEGER>,
    "token_type": <STRING>,
    "scope": <STRING>
}
```

### Validate Token

Check whether the provided token is accepted by the GitHub API.

*Headers*

- **X-GitHub-Token**: GitHub OAuth token to validate.

*Response*

```json
{
    "valid": <BOOLEAN>
}
```

### Defined Fields

Fetch all field keys that may be present in an indexed file object.

*Response*

```json
[
    <STRING>,
    <STRING>,
    <STRING>
]
```

### Get Files

Fetch a specified list of files by pointer URL.

*Headers*

- **X-GitHub-Token**: GitHub OAuth token.

*Params*

- **include_content**: Include file content (boolean).
- **include_last_edit_date**: Include the date of the last commit to the file (boolean).

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
        "last_edit_date": <STRING>,
        "type": <STRING>,
        "source_system": <STRING>,
        "clickable_url": <STRING>,
        "content": <STRING>
    }
]
```

### Stream Files to Index

Stream all files the requesting user has access to that have been added or changed since the last index run.

*Headers*

- **X-GitHub-Token**: GitHub OAuth token.

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
    "content": <STRING>,
    "source_system": <STRING>
}
```
