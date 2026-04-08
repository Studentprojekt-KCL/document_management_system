The following needs to be exported in local environment:

    GITLAB_CONNECTOR_PORT=<CONNECTOR_PORT>
    GITLAB_ADDRESS=<GITLAB_ADDRESS>
    GITLAB_CONNECTOR_BIND_ADDR=<GITLAB_CONNECTOR_BIND_ADDR>
    GITLAB_SYSTEM_NAME=<Name to display in frontend for this Gitlab instance (e.g. 'gitlab').>


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
