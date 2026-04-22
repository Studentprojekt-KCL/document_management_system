The following needs to be exported in local environment:

    
    CONGITLAB_BIND_ADDR=<CONGITLAB_BIND_ADDR>
    CONGITLAB_BIND_PORT=<CONNECTOR_PORT>
    CONGITLAB_GITLAB_URL=<CONGITLAB_GITLAB_URL>
    CONGITLAB_MINIO_ACCESS_ADDRESS=
    CONGITLAB_MINIO_USERNAME=
    CONGITLAB_MINIO_PASSWORD=
    CONGITLAB_SYSTEM_NAME=<Name to display in frontend for this Gitlab instance (eg 'GitLab').>
    CONGITLAB_GITLAB_CLIENT_ID=<Clienct ID of DMIS application in GitLab>
    CONGITLAB_GITLAB_CLIENT_SECRET=<Clienct secret of DMIS application in GitLab>
    CONGITLAB_STATE_SIGNING_SECRET=<Secret in string format used for state signing.>

# Response structure

## Endpoing: file

    {
        "metadata": {
        "unique_pointer": <POINTER TO OBJ>,
        "name": "<FILE NAME>",
        "size": 6042,
        "last_edit_date": <EDIT DATE>,
        "type": <TYPE OF OBJECT>,
        "source_system": "GitLab",
        "clickable_url": <CLICKABLE URL TO OBJ>
    },
        "content": <FILE CONTENT>
    }
