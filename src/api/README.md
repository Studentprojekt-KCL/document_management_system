# Run instaurctions

## Required environment variables

    DMISAPI_BIND_ADDR=<addr api will bind to>
    DMISAPI_BIND_PORT=<port api will bind to>
    DMISAPI_SEARCHENG_URL=<URL pointing to search engine>
    DMISAPI_STOCHAN_URL=<URL pointing to stochastic analyzer>
    DMISAPI_CONGATEWAY_URL=<URL pointing to gateway connector>
    DMISAPI_AD_URL=<URL pointing to AD including realm>
    DMISAPI_AD_JWKS_URL=<JWT public keys endpoint for signature verification>
    DMISAPI_AD_AUTHORIZED_PARTY=<Expected azp claim identifying authorized client application>

## In python venv

    pip install src/api
    dmis_api --dev

## Using docker

### 1. Build the image from the project root:

    sudo docker build -t dmis_api -f src/api/Dockerfile .

### 2. Run the container

    sudo docker run --rm -p <PORT_TO_EXPOSE>:<DMISAPI_BIND_PORT> --env-file src/api/src/.env dmis_api

# Make request to API

## Search engine endpoint

    curl -H 'Authorization: Bearer <ACCESS_TOKEN>' '<API_HOST>/search_engine/search?query=<QUERY>'

## Summery endpoint

    curl -X 'POST' -H 'Authorization: Bearer <ACCESS_TOKEN>' '<API_HOST>/stochastic-analyzer/summarize' -H 'accept: application/json' -d '{"pointers": ["<UNIQUE_FILE_POINTER>"]}'
