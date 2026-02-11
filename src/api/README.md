# DMIS API

The code in this subdirectory contains the package for the main API of DMIS.

## Developer instructions
Run the API locally in developer mode, inside a virtual python environment do the following:

    $ pip install -e src/api
    $ dmis_api --dev

### Test request to API:
To test that the API is working correctly, test the following CURL command:

    curl -X 'GET'   'http://127.0.0.1:8000/index'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{"data": {}}'

This should result in a 422 response containing the following content:

    {"detail":[{"type":"missing","loc":["body","search"],"msg":"Field required","input":{"data":{}}}],"body":{"data":{}}}

### Further API documentation
An automated API documentation is constructed when the API service is initiaded, and can be found at http://127.0.0.1:8000/docs
