# DMIS API

This subdirectory contains the package for the main API of DMIS.

## Developer instructions

Run the API locally in developer mode inside a Python virtual environment

### 1. Install the package

pip install -e src/api

### 2. Create a .env file

nano .env

DMIS_SEARCH_API_URL=http://<ip-address>
API_PORT=XXXX

### 3. Start the API

dmis_api --dev

NOTE: start from directory /src/api/src

### 4. Test request to API:

curl "http://127.0.0.1:8000/search?query=test"

Expected "200 ok" code


### Run with Docker

### 1. Build the image from the project root: 

sudo docker build -t dmis_api -f src/api/Dockerfile .

### 2. Run the container

sudo docker run --rm -p 8000:8000 --env-file src/api/src/.env dmis_api

### 3. Test the API

curl "http://127.0.0.1:8000/search?query=test"

Expected result "200 OK"





