The following needs to be exported in local environment:

    CONGITLAB_BIND_ADDR=<BIND_ADDRESS>
    CONGITLAB_BIND_PORT=<PORT>
    CONGITLAB_GITLAB_URL=<GITLAB_INSTANCE_URL>            # e.g. https://gitlab.com
    CONGITLAB_SYSTEM_NAME=<SOURCE_SYSTEM_NAME>            # e.g. GitLab
    CONGITLAB_REQUEST_TIMEOUT=<SECONDS>                   # e.g. 120
    CONGITLAB_SHARED_CLIENT=<true|false>                  # true: one shared AsyncClient across all download workers; false: each worker owns its own
    MINIO_ACCESS_ADDRESS=<MINIO_URL>                      # e.g. http://minio:9000
    MINIO_USERNAME=<USERNAME>
    MINIO_PASSWORD=<PASSWORD>

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/index_needed_bool` | GET | Returns whether any project has new content since the last index |
| `/stream_files_to_index` | GET | Streams NDJSON — subdata header followed by one file per line |
| `/get_files` | POST | Fetches specific files by pointer |
| `/connected_source_systems` | GET | Returns the configured source system name |
| `/files_to_index` | GET | **Deprecated** — use `/stream_files_to_index` instead |

## Response structure

### `/get_files`

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
