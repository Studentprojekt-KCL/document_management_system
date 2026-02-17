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

Optional flags:

- `--dev`, developer mode
