The following needs to be exported in local environment:

    GITLAB_CONNECTOR_PORT=<CONNECTOR_PORT>
    GITLAB_ADDRESS=<GITLABB_ADDRESS>


# Response structure

## Endpoing: file

    {
    "metadata": {
    "unique_pointer": <POINTER TO OBJ>,
    "name": "<FILE NAME>",
    "size": 6042,
    "last_edit_date": <EDIT DATE>,
    "type": <TYPE OF OBJECT>,
    "source_system": "gitlabs",
    "clickable_url": <CLICKABLE URL TO OBJ>
    },
    "content": <FILE CONTENT>
    }
