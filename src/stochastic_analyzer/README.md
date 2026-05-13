# Stochastic Analyzer Gateway

The code in this subdirectory contains the package for the Stochastic Analyzer Gateway, a service that handles document summarization, merging, and markdown-to-PDF conversion.

## Endpoints

### Summarize

Summarize one or more documents.

- `pointers`: list of file pointers, required (1 or more).

```url
http://<host>:<port>/summarize
```

```json
{
    "pointers": ["<file pointer>", "<file pointer>", ...]
}
```

Response:

```json
{
    "summary": "<summary text>"
}
```

### Merge

Merge multiple documents into one coherent document.

- `pointers`: list of file pointers, required (2 or more).

```url
http://<host>:<port>/merge
```

```json
{
    "pointers": ["<file pointer>", "<file pointer>", ...]
}
```

Response:

```json
{
    "summary": "<merged document>"
}
```

### Markdown to PDF

Convert a markdown string into a PDF file.

- `markdown`: markdown string, required.

```url
http://<host>:<port>/md-to-pdf
```

```json
{
    "markdown": "<markdown string>"
}
```

Response: PDF file (`application/pdf`).

## Developer Instructions

Run the gateway locally inside a virtual python environment:

```bash
$ pip install -e .
$ stochastic-analyzer
```

## Further API documentation

Automated API documentation is constructed when the service is initiated, and can be found at http://127.0.0.1:8000/docs

## Configuration

Configuration is done through environment variables.

```env
STOCHAN_BIND_ADDR=<Gateway bind address>
STOCHAN_BIND_PORT=<Gateway port>
STOCHAN_CONGATEWAY_URL=<Connector address>
STOCHAN_LLM_URL=<LLM endpoint URL>
STOCHAN_LLM_MODEL=<LLM model name>
```