# GitLab Connector

Communicates with a GitLab and manages file delivery.

## Confiuration

### Environment Variables

- **CONGITLAB_BIND_ADDR**: Which address to bind to.
- **CONGITLAB_BIND_PORT**: Which port to bind to.
- **CONGITLAB_GITLAB_URL**: URL to GitLab instance.
- **CONGITLAB_SYSTEM_NAME**: Name for this specific GitLab instance (to be shown in frontend).
- **CONGITLAB_GITLAB_CLIENT_ID**: Clienct ID of DMIS application in GitLab.
- **CONGITLAB_GITLAB_CLIENT_SECRET**: Clienct secret of DMIS application in GitLab.
- **CONGITLAB_STATE_SIGNING_SECRET**: Secret in string format used for state signing.
- **CONGITLAB_CONNECT_SERVICE_CALLBACK**: Service to refere GitLab to send redirect to (usually frontend session/callback endpoint).


### Flags

- `--dev`: Enable dev prints.

## Behaviour

The connector uses the subdata variable to identify changed or new files, in this case the subdata is an encoded dict comprised of last date a GitLab project was indexed (where the date is the newest version of the project at that time). This implementation is done since different users have access to different projects.

Connector will stream; all files in all projects which has been updated since the specified latest update for that paricular project in the subdata.

## Endpoints

|Endpoint|Method|Description|
|--------|------|-----------|
|`/get_files`|POST|Grab a specified list of files.|
|`/stream_files_to_index`|POST|Stream all reachable and *new* files.|
|`/defined_fields`|GET|Grab all the defined fields a file could have.|
|`/auth_user`|GET|Redirect to session authentication for user.|
|`/callback`|GET|Possible callback for session authentication.|
|`/refresh_token`|GET|Refresh session token in GitLab.|
|`/validate_token`|GET|Validates the Session token.|

### Get Files

Fetch all specified files.

*Headers*

- **x_gitlab_token**: basic authorization header.

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

*Response*

```json
[
    {
        "unique_pointer": <STRING>,
        "field-1": <STRING>
    },
    {
        "unique_pointer": <STRING>,
        "field-1": <STRING>
    }
]
```

### Stream Files to Index

Stream all files which the requesting user has access to.

*Headers*

- **x_gitlab_token**: basic authorization header.

*Body*

```json
{"subdata": <STRING>}
```

*Response*

Note it is sent as a stream.

```json
{"subdata": <STRING>}
{
    "unique_pointer": <STRING>,
    "field-1": <STRING>
}
```

### Defined Fields

Fetch all defined file fields.

*Response*:

```json
[
    <STRING>,
    <STRING>,
    <STRING>
]
```

### Validate Token

Validate the authentication token, in this case an basic authorization header.

*Headers*

- **x_gitlab_token**: Bearer auth header.

*Response*

```json
{
    "valid": <BOOLEAN>
}
```
