The following must be exported in the local environment:

    GITHUB_API_URL=<GITHUB_API_BASE_URL>        # e.g. https://api.github.com/
    GITHUB_SYSTEM_NAME=<SOURCE_SYSTEM_NAME>
    GITHUB_API_VERSION=<API_VERSION>            # e.g. 2022-11-28
    GITHUB_AUTH_MODE=legacy|app|auto
    GITHUB_CONNECTOR_HOST=<BIND_ADDRESS>
    GITHUB_CONNECTOR_PORT=<PORT>

Optional:

    GITHUB_TOKEN=<TOKEN>                        # legacy personal access token
    GITHUB_ACCESS_TOKEN=<TOKEN>                 # preferred over GITHUB_TOKEN if both set
    GITHUB_APP_INSTALLATION_TOKEN=<TOKEN>       # used when GITHUB_AUTH_MODE=app; preferred over legacy tokens in auto mode
    GITHUB_ORG=<ORG_LOGIN>                      # if set, fetches org repos instead of user repos
    GITHUB_EXCLUDE_PATHS=<COMMA_SEPARATED>      # path substrings to exclude from indexing
