# Main interface to contact source system connects


All requests for source system connectors should be routed through this service.

## Build and run container
1. Navigate to root directory of reposity
```bash
docker build \
 -f src/connectors/connector-gateway/Dockerfile \
 -t connector-gateway:dev .
```

2. Create source-systems.json (config file)
```bash
tee src/connectors/connector-gateway/source_systems.json > /dev/null <<'EOF'
[
  {
    "name": "Gitlab",
    "connector_url": <CONNECTOR_HOST>,
    "source_system_url": <SOURCE_HOST>,
    "authentication_method": "session",
    "authentication_header": "x_gitlab_token",
    "token_type": "bearer"
  },
  {
    "name": "SMB",
    "connector_url": <CONNECTOR_HOST>,
    "source_system_url": <SOURCE_HOST>,
    "authentication_method": "BA",
    "authentication_header": "authorization",
    "token_type": "Basic"
  }
]

EOF
```

3. Run image

```bash
docker run \
  -p 8080:80 \
  -v ./src/connectors/connector-gateway/source_systems.json:/etc/source-systems.json \
  -e CONGATEWAY_FASTAPI_BIND_ADDR=0.0.0.0 \
  -e CONGATEWAY_FASTAPI_BIND_PORT=80 \
  -e CONGATEWAY_FASTAPI_LOG_LEVEL=debug \
  -e CONGATEWAY_CONFIG_FILE_PATH=/etc/source-systems.json \
  -e CONGATEWAY_REQUEST_TIMEOUT=120 \
  connector-gateway:dev
```


## Required env vars

    CONGATEWAY_FASTAPI_BIND_ADDR
    CONGATEWAY_FASTAPI_BIND_PORT
    CONGATEWAY_FASTAPI_LOG_LEVEL
    CONGATEWAY_CONFIG_FILE_PATH
    CONGATEWAY_REQUEST_TIMEOUT
    CONGATEWAY_REFRESH_SERVICE_URL
