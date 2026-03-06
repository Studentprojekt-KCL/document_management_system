# Search engine

The code in this subdirectory contains the package for the Search engine.

## Developer Instructions

Run the Search Engine locally in developer mode, inside a virtual python environment do the following:

```bash
$ pip install -e .
$ search_engine --dev
```

## Test request to API

To test that the API is working correctly, test the following CURL command:

```bash
curl -v http://127.0.0.1:8000/health
```

Which should result in a `200` and:

```json
{
    "msg":"healthy"
}
```

## Further API documentation

An automated API documentation is constructed when the API service is initiaded, and can be found at http://127.0.0.1:8000/docs

## Configuration

Configuration is done through environment variables.

- `SE_API_PORT` Search engine port.
- `SE_API_CONNECTOR_ADDRESS` Connector address.
- `SE_API_MULTIPLIER_NAME` how heavy the result of the name field is, optional.
- `SE_API_MULTIPLIER_EDITED`  how heavy the result of the edited field is, optional.
- `SE_API_MULTIPLIER_TYPE` how heavy the result of the type field is, optional.
- `SE_API_MULTIPLIER_CONTENT` how heavy the result of the content field is, optional.
- `SE_API_MULTIPLIER_SIZE` how heavy the result of the size field is, optional.

Optional flags:

- `--dev`, developer mode
