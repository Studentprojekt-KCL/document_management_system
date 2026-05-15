The following must be exported in the local environment:

    CONGITHUB_BIND_PORT=<PORT>
    CONGITHUB_BIND_ADDR=<BIND_ADDRESS>
    CONGITHUB_GITHUB_API_URL=<GITHUB_API_BASE_URL>        # REST API root — github.com: https://api.github.com/  |  GHE: https://<host>/api/v3/
    CONGITHUB_GITHUB_BASE_URL=<GITHUB_BASE_URL>           # Web root for OAuth redirects — github.com: https://github.com  |  GHE: https://<host>
    CONGITHUB_GITHUB_SYSTEM_NAME=<SOURCE_SYSTEM_NAME>
    CONGITHUB_GITHUB_API_VERSION=<API_VERSION>            # e.g. 2022-11-28
    CONGITLAB_CONNECT_SERVICE_CALLBACK=<Service to refere GitLab to send redirect to>

Note: GITHUB_API_URL and GITHUB_BASE_URL are different because on github.com the REST API
lives on a separate subdomain (api.github.com) from the OAuth endpoints (github.com).
They cannot be derived from each other without hardcoding that special case.

OAuth (required for `/auth_user`, `/callback`, `/refresh_token`):

    CONGITHUB_CLIENT_ID=<GITHUB_APP_CLIENT_ID>
    CONGITHUB_CLIENT_SECRET=<GITHUB_APP_CLIENT_SECRET>
    CONGITHUB_STATE_SIGNING_SECRET=<HMAC_SECRET>           # random secret for CSRF state signing

Optional:

    CONGITHUB_GITHUB_ORG=<ORG_LOGIN>
    CONGITHUB_GITHUB_EXCLUDE_PATHS=<COMMA_SEPARATED>      # path substrings to exclude from indexing

`CONGITHUB_GITHUB_ORG` is the organisation's login - the URL slug that appears in `github.com/<org-login>`.
When set, the connector indexes that organisation's repositories instead of the authenticated user's repositories.
The GitHub App must be installed on the organisation; repo-level access can be limited at installation time.

## Authentication

### Per-request token
File indexing endpoints accept the user's GitHub OAuth token in the `X-GitHub-Token` header:

    X-GitHub-Token: <user token>

If the header is absent the connector returns an empty result — no GitHub API calls are made.

### OAuth flow
The connector implements a full OAuth2 authorization-code flow via a GitHub App (user-to-server).
Permissions are configured in the GitHub App settings

Required GitHub App permissions:
- **Metadata: Read-only** — list repositories
- **Contents: Read-only** — download repo archives and read file content

Org repo access (`CONGITHUB_GITHUB_ORG`) is gated by whether the GitHub App is installed on
that org, not by any additional permission.

1. Call `GET /auth_user`. The connector redirects the user to GitHub's consent page.
2. GitHub redirects back to `/callback?code=…&state=…`.
   The connector validates the state signature and exchanges the code for tokens, returning JSON.
3. Use the returned `access_token` in subsequent `X-GitHub-Token` headers.
4. GitHub Apps always issue expiring tokens — call `GET /refresh_token` with a `refresh-token` header
   to obtain a new token pair before expiry (tokens last 8 hours, refresh tokens 6 months).

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/auth_user` | GET | Redirects user to GitHub OAuth consent page |
| `/callback` | GET | Exchanges GitHub authorization code for access/refresh tokens |
| `/refresh_token` | GET | Refreshes an expiring access token (`refresh-token` header required) |
| `/defined_fields` | GET | Lists field keys returned for indexed documents (gateway union contract) |
| `/stream_files_to_index` | POST | Streams NDJSON — JSON body ``{"subdata": ...}``, then one file per line (same as GitLab) |
| `/get_files` | POST | Fetches specific files by pointer |
