# Run instructions

## Required environment variables

    DMISAPI_BIND_ADDR=<addr api will bind to>
    DMISAPI_BIND_PORT=<port api will bind to>

    DMISAPI_SEARCHENG_URL=<URL pointing to search engine>
    DMISAPI_STOCHAN_URL=<URL pointing to stochastic analyzer>
    DMISAPI_CONGATEWAY_URL=<URL pointing to gateway connector>
    DMISAPI_LOGAPI_URL=<URL pointing to the log API>

    DMISAPI_AD_URL=<URL pointing to the the identity of the provider (realmn)>
    DMISAPI_AD_JWKS_URL=<JWT public keys endpoint for signature verification>
    DMISAPI_AD_AUDIENCE=<Expected audience (aud claim) for this API, comma separated if multiple>
    DMISAPI_AD_ALLOWED_AZP=<Allowed authorized party (azp claim), comma separated if multiple>

    DMISAPI_SEARCHENG_SCOPE=<Required scope name(s) for search engine endpoints, space-separated if multiple>
    DMISAPI_STOCHAN_SCOPE=<Required scope name(s) for stochastic analyzer endpoints, space-separated if multiple>
    DMISAPI_CONGATEWAY_SCOPE=<Required scope name(s) for connector endpoints, space-separated if multiple>


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

## Summary endpoint

    curl -X 'POST' -H 'Authorization: Bearer <ACCESS_TOKEN>' '<API_HOST>/stochastic-analyzer/summarize' -H 'accept: application/json' -d '{"pointers": ["<UNIQUE_FILE_POINTER>"]}'
