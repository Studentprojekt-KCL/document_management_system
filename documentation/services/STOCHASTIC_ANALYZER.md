# Stochastic Analyzer Gateway

The Stochastic Analyzer Gateway is a service that handles document summarization, merging, and markdown-to-PDF conversion.

## Configuration

### Environment variables

- **STOCHAN_BIND_ADDR**: Gateway bind address.
- **STOCHAN_BIND_PORT**: Gateway port.
- **STOCHAN_CONGATEWAY_URL**: Connector address.
- **STOCHAN_LLM_URL**: LLM endpoint URL.
- **STOCHAN_LLM_MODEL**: LLM model name.

## Behaviour

Every summarization or merge request initiates a processing pipeline. Depending on the request, the pipeline is structured in the following way:

- Fetch file contents from the connector gateway using the provided file pointers.
- Decode the payloads and extract text using MarkItDown or UTF-8 fallback.
- For single document summaries, the LLM is prompted directly for a summary.
- For multiple documents (summarize or merge), a two-stage LLM pipeline is executed:
  1. Extract the main content of each document individually to concise prose.
  2. Combine the extracts and perform a final summarization or merge operation.
- For markdown to PDF requests, the service bypasses the connector and converts the provided markdown string directly into a formatted PDF byte stream.

The two-stage pipeline for multiple documents prevents the LLM context window from being overwhelmed by extracting information from each document before attempting the final merge or summary.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
|`/summarize`|POST|Summarize one or more documents.|
|`/merge`|POST|Merge multiple documents into one coherent document.|
|`/md-to-pdf`|POST|Convert a markdown string into a PDF file.|

### Summarize

Summarize one or more documents. 

*Header*

- `authorization`: Authorization token.

*Body*

```json
{
    "pointers": [
        "<file pointer-1>",
        "<file pointer-2>"
    ]
}
```

*Response*

```json
{
    "summary": "<summary text>"
}
```

### Merge

Merge multiple documents into one coherent document. Requires a minimum of 2 pointers.

*Header*

- `authorization`: Authorization token.

*Body*

```json
{
    "pointers": [
        "<file pointer-1>",
        "<file pointer-2>"
    ]
}
```

*Response*

```json
{
    "summary": "<merged document>"
}
```

### Markdown to PDF

Convert a markdown string into a PDF file.

*Body*

```json
{
    "markdown": "<markdown string>"
}
```

*Response*

Returns a PDF file (`application/pdf`) with the header `Content-Disposition: attachment; filename='summary.pdf'`.
