# DMIS API

This subdirectory contains the package for the main API of DMIS.

## Env file

Put the following in a .env file.

    DMIS_SEARCH_API_URL=<SEARCH_ENGINE_ADDRESS>
    DMIS_SUMMARY_API_URL=<SUMMARY_ADDRESS>
    API_PORT=<PORT_TO_EXPOSE>


# Developer instructions


Run the API locally in developer mode inside a Python virtual environment

### 1. Export variables in local env

    export DMIS_SEARCH_API_URL = <SEARCH_ENGINE_ADDRESS>
    export DMIS_SUMMARY_API_URL = <SUMMARY_ADDRESS>
    export API_PORT = <PORT_TO_EXPOSE>
    export API_BIND_ADDRESS = <ADDRESS_TO_BIND_TO>
    export API_ALLOW_ORIGIN = <COMMA_SEPERATED_LIST_OF_ALLOWED_ORIGINS (localhost:8000,127.0.0.1:1919,...)>

### 2. Install the package

pip install -e src/api

### 3. Start the API

dmis_api --dev

### 4. Test request to API:

curl "http://127.0.0.1:8001/docs"

Expected "200 ok" code

## Run with Docker

Create .env in src/api/src

nano .env
DMIS_SEARCH_API_URL=http://<ip-address>
DMIS_QUERY_API_URL=http://<ip-adress>
API_PORT=XXXX
API_BIND_ADDRESS=0.0.0.0
API_ALLOW_ORIGIN=http://localhost:8000

### 1. Build the image from the project root: 

sudo docker build -t dmis_api -f src/api/Dockerfile .

### 2. Run the container

sudo docker run --rm -p 8001:8001 --env-file src/api/src/.env dmis_api

### 3. Test the API's

#### Testing main API endpoint
curl "http://127.0.0.1:8001/docs"

#### Testing search API endpoint
curl "http://127.0.0.1:8001/search?query=test"

#### Testing summary API endpoint
curl -X POST "http://127.0.0.1:8001/summary" \
  -H "Content-Type: application/json" \
  -d '{"file_pointer":"THEFILEPOINTER"}'

## Endpoint List ! OBS ! REMOVE WHEN PUSHING INTO DEVELOP BRANCH
DMIS_SEARCH_API_URL=http://search-engine.dev.dms-lookup.com:8000
API_PORT=8001
DMIS_QUERY_API_URL=http://gpu-srv-1.prod.h472c.bth.dms-lookup.com:8000
API_BIND_ADDRESS=0.0.0.0
API_ALLOW_ORIGIN=http://localhost:8000
