The following needs to be exported in local environment:

    GITLAB_CONNECTOR_PORT=<CONNECTOR_PORT>
    GITLAB_ADDRESS=<GITLAB_ADDRESS>
    GITLAB_CONNECTOR_BIND_ADDR=<GITLAB_CONNECTOR_BIND_ADDR>
    GITLAB_SYSTEM_NAME=<Name to display in frontend for this Gitlab instance (e.g. 'gitlab').>

## Authentication

Authentication is per-request, not configured at startup. Callers must supply the user's GitLab
personal access token (or OAuth token) in the `X-GitLab-Token` request header:

    X-GitLab-Token: <user token>

If the header is absent the connector returns an empty result for that request — no GitLab API
calls are made. There is no service-level fallback token.


# Response structure

## Endpoing: file

    {
    "metadata": {
    "unique_pointer": <POINTER TO OBJ>,
    "name": "<FILE NAME>",
    "size": 6042,
    "last_edit_date": <EDIT DATE>,
    "type": <TYPE OF OBJECT>,
    "source_system": "gitlab",
    "clickable_url": <CLICKABLE URL TO OBJ>
    },
    "content": <FILE CONTENT>
    }
