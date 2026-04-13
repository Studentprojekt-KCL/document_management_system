# Search engine

The code in this subdirectory contains the package for the Search engine.

## Endpoints

### Search

Performs a search and returns the metadata for the result.

- `query`: search query, required.
- `count`: page size, default 10.
- `offset`: page index, default 0.

```url
http://<host>:<port>/search?q=<search query>&k=<page size>&p=<page index>
```

Response can vary depending on what the connector gives.

```json
[
    {
        "unique_pointer": <file pointer>
    },
    {
        "unique_pointer": <file pointer>
    },
    ...
]
```

### Health

Checks if the connection to connector is healthy, (doesnt atm).

```url
http://<host>:<port>/health
```

```json
{
    "msg":<status>
}
```

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
- `SE_API_HOST` Search engine bind address.
- `SE_API_CONNECTOR_ADDRESS` Connector address.
- `SE_API_QUERY_ADDRESS` Query address.
- `SE_API_CACHE_DIRECTORY` Cache file location.

Optional flags:

- `--dev`, developer mode
