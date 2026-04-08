
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
KEYCLOAK_ISSUER=https://KEYCLOAK_IP/realms/master
KEYCLOAK_AUDIENCE=FRONTEND_IP
KEYCLOAK_JWKS_URL=https://KEYCLOAK_IP/realms/master/protocol/openid-connect/certs

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
