# Run instaurctions

## Required environment variables

    DMIS_SEARCH_API_URL=<DMIS_SEARCH_API>
    DMIS_QUERY_API_URL=<DMIS_QUERY_API>
    API_PORT=XXXX
    API_BIND_ADDRESS=<BIND_ADDR>

## In python venv

    pip install src/api
    dmis_api --dev

## Using docker

### 1. Build the image from the project root:

sudo docker build -t dmis_api -f src/api/Dockerfile .

### 2. Run the container

sudo docker run --rm -p 8001:8001 --env-file src/api/src/.env dmis_api

# Make request to API

## Search engine endpoint

    curl '<API_HOST>/search_engine/search?query=<QUERY>'

## Summery endpoint

    curl -X 'POST' '<API_HOST>/stochastic-analyzer/summarize' -H 'accept: application/json' -d '{"pointers": ["<UNIQUE_FILE_POINTER>"]}'
