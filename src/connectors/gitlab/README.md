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

# Calling examples

    curl <HOST>/auth_user -H 'callback-url: <CALLBACK_URL>'
