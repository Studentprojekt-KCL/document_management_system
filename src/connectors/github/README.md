The following must be exported in the local environment:

    CONGITHUB_BIND_PORT=<PORT>
    CONGITHUB_BIND_ADDR=<BIND_ADDRESS>
    CONGITHUB_GITHUB_API_URL=<GITHUB_API_BASE_URL>        # e.g. https://api.github.com/
    CONGITHUB_GITHUB_SYSTEM_NAME=<SOURCE_SYSTEM_NAME>
    CONGITHUB_GITHUB_API_VERSION=<API_VERSION>            # e.g. 2022-11-28

Optional:

    CONGITHUB_GITHUB_ORG=<ORG_LOGIN>                      # if set, fetches org repos instead of user repos
    CONGITHUB_GITHUB_EXCLUDE_PATHS=<COMMA_SEPARATED>      # path substrings to exclude from indexing

## Authentication

Authentication is per-request, not configured at startup. Callers must supply the user's GitHub
personal access token (or OAuth token) in the `X-GitHub-Token` request header:

    X-GitHub-Token: <user token>

If the header is absent the connector returns an empty result for that request — no GitHub API
calls are made. There is no service-level fallback token.
