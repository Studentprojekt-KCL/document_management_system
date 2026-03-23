# DMIS API

This subdirectory contains the package for the main API of DMIS.

## Env file

Put the following in a .env file.

    DMIS_SEARCH_API_URL=<SEARCH_ENGINE_ADDRESS>
    API_PORT=<PORT_TO_EXPOSE>


## Developer instructions

Run the API locally in developer mode inside a Python virtual environment

### 1. Export variables in local env

    export DMIS_SEARCH_API_URL = <SEARCH_ENGINE_ADDRESS>
    export API_PORT = <PORT_TO_EXPOSE>

### 2. Install the package

pip install -e src/api

### 3. Start the API

dmis_api --dev

### 4. Test request to API:

curl "http://127.0.0.1:8000/search?query=test"

Expected "200 ok" code

## Run with Docker

### 1. Build the image from the project root: 

sudo docker build -t dmis_api -f src/api/Dockerfile .

### 2. Run the container

sudo docker run --rm -p 8000:8000 --env-file .env dmis_api

### 3. Test the API

curl "http://127.0.0.1:8000/search?query=test"

Expected result "200 OK"
