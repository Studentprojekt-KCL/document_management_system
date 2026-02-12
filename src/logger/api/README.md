# Logger Service API

The code in this subdirectory contains the package for the API of the Loggin Service.

## Developer Instructions

Run the API locally in developer mode, inside a virtual python environment do the following:

```bash
$ pip install -e .
$ log_api --dev
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

- `LOGGER_DB_HOST` Database host.
- `LOGGER_DB_USER` Database user.
- `LOGGER_DB_PASS` User password for database.
- `LOGGER_DB_DATABASE` Database name.

Optional flags:

- `--dev`, developer mode
