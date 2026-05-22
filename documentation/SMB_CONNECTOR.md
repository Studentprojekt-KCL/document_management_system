# SAMBA Connector

Communicates with a SMB server and manages file delivery.

## Confiuration

### Environment Variables

- **CONSMB_BIND_ADDR**: Which address to bind to.
- **CONSMB_BIND_PORT**: Which port to bind to.
- **CONSMB_SMB_SHARE_ADDR**: Address to the server hosting the SMB.
- **CONSMB_SMB_SHARE_PORT**: Port to access the SMB.
- **CONSMB_SMB_SHARE_NAME**: Name of the SMB share.
- **CONSMB_SMB_SHARE_SERVICE_USER**: Service user.
- **CONSMB_SMB_SHARE_SERVICE_PASS**: Service user password.
- **CONSMB_SMB_SERVICE_MOUNT_PATH**: Path to mount the partion as the service user.
- **CONSMB_SMB_USER_MOUNT_PATH**: Path to mount the partion as a user.
- **CONSMB_SYSTEM_NAME**: Name of the connector, visable in the frontend.

### Flags

- `--dev`: Enable dev prints.

## Behaviour

## Endpoints

|Endpoint|Method|Description|
|--------|------|-----------|
|`/get_files`|POST|Grab a specified list of files.|
|`/stream_files_to_index`|POST|Stream all reachable and *new* files.|
|`/defined_fields`|GET|Grab all the defined fields a file could have.|
|`/validate_token`|GET|Validates the given credentials.|


### Get Files

Fetch all specified files.

*Headers*

- **authorization**: basic authorization header.

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
