The following needs to be exported in local environment:

    CONSHAREPOINT_BIND_ADDR=<BIND_ADDRESS>
    CONSHAREPOINT_BIND_PORT=<CONNECTOR_PORT>
    CONSHAREPOINT_SYSTEM_NAME=<Name to display in frontend for this SharePoint instance (e.g. 'SharePoint')>
    CONSHAREPOINT_TENANT_ID=<Azure AD tenant ID — found in Azure portal: Entra ID → Overview>
    CONSHAREPOINT_CLIENT_ID=<Client ID of DMIS application registered in Azure AD>
    CONSHAREPOINT_CLIENT_SECRET=<Client secret of DMIS application in Azure AD>
    CONSHAREPOINT_STATE_SIGNING_SECRET=<Secret string used for OAuth state signing>

# Azure AD App Registration

Register an app in portal.azure.com (Entra ID → App registrations) with:
- Delegated API permissions: `Sites.Read.All`, `Files.Read.All`, `offline_access`
- Redirect URI pointing to: `http(s)://<connector-host>/callback`

`Sites.Read.All` requires admin consent in enterprise/education tenants.

# Authentication

Authentication is per-user OAuth 2.0 managed by the connector:

1. Caller redirects the user to `/auth_user` — connector redirects to Microsoft login
2. Microsoft redirects back to `/callback` — connector exchanges the code for access and refresh tokens and returns them to the caller for storage
3. On every subsequent request the caller supplies the access token in the `X-SharePoint-Token` header
4. `/refresh_token` renews an expired access token using the stored refresh token

# Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/index_needed_bool` | GET | Returns whether any files have changed since the last sync |
| `/stream_files_to_index` | GET | Streams NDJSON — subdata header followed by one file per line |
| `/get_files` | POST | Fetches specific files by unique pointer |
| `/auth_user` | GET | Redirects user to Microsoft OAuth login |
| `/callback` | GET | Exchanges authorization code for access and refresh tokens |
| `/refresh_token` | GET | Renews an access token using a refresh token |

# Response structure

## Endpoint: /get_files

    {
        "unique_pointer": <GRAPH API URL TO ITEM>,
        "name": "<FILE NAME>",
        "size": 1024,
        "last_edit_date": <ISO EDIT DATE>,
        "type": "source_file",
        "source_system": "SharePoint",
        "clickable_url": <WEB URL TO FILE>,
        "file_type": ".pdf",
        "file_type_description": "PDF"
    }

## Endpoint: /stream_files_to_index

First line: `{"subdata": "<base64-encoded delta token map>"}`

Pass this subdata value back on the next call to receive only changed files (delta sync).
Omit it to perform a full scan.

Subsequent lines (one per qualifying document):

    {
        "content": null,
        "metadata": {
            "unique_pointer": <GRAPH API URL TO ITEM>,
            "name": "<FILE NAME>",
            "size": 1024,
            "last_edit_date": <ISO EDIT DATE>,
            "type": "source_file",
            "source_system": "SharePoint",
            "clickable_url": <WEB URL TO FILE>,
            "file_type": ".pdf",
            "file_type_description": "PDF"
        }
    }
