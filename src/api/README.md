# DMIS API

This subdirectory contains the package for the main API of DMIS.

## Environment Configuration

Create a .env file with the following variables:

- DMIS_API_SEARCH_URL=<DMIS_SEARCH_API>
- DMIS_API_QUERY_URL=<DMIS_QUERY_API>
- DMIS_API_CONNECTOR_URL=<CONNECTOR_URL>
- DMIS_API_PORT=XXXX
- DMIS_API_BIND_ADDRESS=<BIND_ADRESS>

- DMIS_API_KEYCLOAK_ISSUER=https://<KEYCLOAK_HOST>/realms/master
- DMIS_API_KEYCLOAK_JWKS_URL=https://<KEYCLOAK_HOST>/realms/master/protocol/openid-connect/certs
- DMIS_API_KEYCLOAK_EXPECTED_AZP=<CLIENT_ID>

## Developer Setup (Local)

Run the API locally in development mode using a Python virtual environment.

### 1. Set Enviroment Variables

- export DMIS_API_SEARCH_URL=<DMIS_SEARCH_API>
- export DMIS_API_QUERY_URL=<DMIS_QUERY_API>
- export DMIS_API_CONNECTOR_URL=<CONNECTOR_URL>
- export DMIS_API_PORT=XXXX
- export DMIS_API_BIND_ADDRESS=<BIND_ADRESS>

- export DMIS_API_KEYCLOAK_ISSUER=https://<KEYCLOAK_HOST>/realms/master
- export DMIS_API_KEYCLOAK_JWKS_URL=https://<KEYCLOAK_HOST>/realms/master/protocol/openid-connect/certs
- export DMIS_API_KEYCLOAK_EXPECTED_AZP=<CLIENT_ID>

### 2. Install the package
- pip install -e src/api

### 3. Run the API

- dmis_api --dev

### 4. Verify the API

curl -i -H "Authorization: Bearer <ACCESS_TOKEN>" "http://127.0.0.1:8001/search_engine?query=test"

Expected response "200 OK"

## Run with Docker

Create a .env file with the required variables from the section "Environment Configuration"

### 1. Build the image from the project root:

- sudo docker build -t dmis_api -f src/api/Dockerfile .

### 2. Run the container

- sudo docker run --rm -p 8001:8001 --env-file PATH_TO_.ENV/.env dmis_api

## Test the API endpoints

#### Testing search API endpoint
curl -i -H "Authorization: Bearer <ACCESS_TOKEN>" "http://127.0.0.1:8001/search_engine?query=test"

#### Testing summary API endpoint
curl -X POST "http://127.0.0.1:8001/stochastic-analyzer/summary" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"file_pointer": ["THEFILEPOINTER"]}'
