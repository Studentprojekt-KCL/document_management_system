# Gatway Connector

The gateway connector routes all traffic aimed for connector layer to the correct connector, togethger with generating composed datasets where needed from connector layer.

## Confiuration

### Env vars

- **CONGATEWAY_FASTAPI_BIND_ADDR**:  Which address to bind to.
- **CONGATEWAY_FASTAPI_BIND_PORT**: Which port to bind to.
- **CONGATEWAY_FASTAPI_LOG_LEVEL**: Log level for service.
- **CONGATEWAY_CONFIG_FILE_PATH**: Path to source_systems.json file.
- **CONGATEWAY_REQUEST_TIMEOUT**: Timeout in seconds for HTTP request.
- **CONGATEWAY_REFRESH_SERVICE_URL**: URL for refresh-service.

### source_systems.json config file

The following config file is required, used for instructing gateway which connectors exists.
```json
[
  {
    "name": "<CONNECTOR_NAME>",
    "connector_url": <CONNECTOR_HOST>,
    "source_system_url": <SOURCE_HOST>,
    "authentication_method": "session|BA",
    "authentication_header": "<CONNECTO AUTH HEADER (e.g. x_gitlab_token)>",
    "token_type": "<TOKEN TYPE>"
  },
]
```

## Endpoints


|Endpoint|Method|Description|
|--------|------|-----------|
|`/get_files`|POST|Grab a specified list of files from connector layer.|
|`/stream_files_to_index`|GET|Retrieve pointer to all connector layer streaming endpoints.|
|`/connected_source_systems`|GET|List of names of all connected source systems.|
|`/defined_fields`|GET|List of all defined data fields in connectors.|
|`/get_auth_user_urls`|GET|Pointers to auth_user session authentication URLs.|
|`/auth_user`|GET|Auth user for a given service.|
|`/session-callback`|GET|Callback with exchange code for session authentication.|
|`/active-sessions`|GET|See which services currently have valid authorization tokens.|

### Get Files

Fetch all specified files.

*Params*

- **include_content**: to include content or not (boolean).
- **include_last_edit_date**: to include the last edit date (boolean).

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
