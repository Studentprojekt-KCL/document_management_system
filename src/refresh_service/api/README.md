# Required env varaibles

    REFSERVICE_BIND_ADDR=<>
    REFSERVICE_BIND_PORT=<>
    REFSERVICE_SESSION_ENC_PASSW=<>
    REFSERVICE_REDIS_HOST=<>
    REFSERVICE_REDIS_PORT=<>
    REFSERVICE_AD_JWKS_URL=<>
    REFSERVICE_AD_URL=<>

# Run instructions

## Docker build

    sudo docker build -t refresh_service -f src/refresh_service/api/Dockerfile .

## Docker run

    sudo docker run --env-file .env refresh_service /usr/local/bin/refresh-service
    sudo docker run --env-file .env refresh_service /usr/local/bin/refresh-worker

## Add session
```
curl -X 'POST'   '<REFSERVICE_HOST>/add_session?service_name=<SERVICE_NAME>'   -H 'authorization: <DMIS_AD_TOKEN>'-H 'Content-Type: application/json'   -d '{"refresh_url": "<REFRESH_URL>", "session_variables": <SERVICE_OAUTH_TOKEN>'
```

Where session variables should have a structure like:

    {"access_token": "","token_type":"Bearer","expires_in":<OPTIONAL_INT>,"refresh_token":"","scope":"","created_at":<OPTIONAL_INT>}}
