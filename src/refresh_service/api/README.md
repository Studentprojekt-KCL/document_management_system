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
