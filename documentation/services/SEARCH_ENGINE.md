# Search Engine

## Configuration

### Environment variables

- **SEARCHENG_BIND_PORT**: Which port to bind to.
- **SEARCHENG_BIND_ADDR**: Which address to bind to.
- **SEARCHENG_CONGATEWAY_URL**: Connector gateway url.
- **SEARCHENG_WORKING_DIRECTORY**: Directory where the index and other persistent data is stored.
- **SEARCHENG_CLASSIFIER_URL**: Classifier url.
- **LOG_API_URL**: Logger url.

### Flags

- `--dev`: Enable dev prints.

## Behaviour

Every search initializes a new indexing task in the index pipeline, unless an indexing task for an already streaming source connector is recieved.
Then it'll skip that connector till it is finished and another request is performed. The pipeline is strutured in the following way, note these steps occur concurrently:

- Fetch streaming endpoints from the connector gateway.
- Recieve the stream from the connector.
- Decode and format each file and detect potential documents.
- Index a batch of file.
- Fetch file content from index.
- Classify batch of files.
- Reindex the files in batches.

The reason the files are re fetched from the index instead of storing them in memory until it's done, is the slow nature of the classifier.
The memory will run out long before the classifications are finished and this allows the search engine to save memory by writing to storage
while waiting for the next availabe classification spot. 

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
|`/search`|POST|Search through the index.|
|`/check_health`|GET|Check instance health.|
|`/reset`|POST|Reset the search engine, zero all the indexes.|
|`/classification`|POST|Set classification for a file|
|`/classifications`|GET|Get a list of available classifications|
|`/file_types`|GET|Get all defined file types.|
|`/file_types_documents_only`|GET|Get all document types|
|`/find_matching`|GET|Get files matching the original|
|`/searchable_fields`|GET|Get all searchable fields|

### Search

Search through the files in the index.

*Header*

- `authorization`: Authorization token.

*Params*

- **Count**: maximum amount of results.
- **Offset**: offset, used for e.g paging.

*Body*

```json
{
    "field-1": <STRING>,
    "field-2": <STRING>,
    "file_type": "extension-1 extention-2 extention-3",
    "documents_only": <BOOLEAN>
    "modified": <BOOLEAN>
}
```

*Response*

```json
[
    {
        "unique_pointer": <STRING>,
        "field-1": <STRING>
    },
    {
        "unique_pointer": <STRING>,
        "field-1": <STRING>
    }
]
```

### Check Health

Check the status of the search engine.

*Response*

```json
{
    "msg": "healthy"
}
```

### Reset

Reset the search engine. Removes and rebuilds the index and stored data.

### Classification

Set the classification of a single file.

*Header*

- `authorization`: Authorization token.

*Body*

```json
{
    "unique_pointer": <STRING>,
    "security_class": <STRING>
}
```

*Response*

```json
{
    "unique_pointer": <STRING>,
    "field-1": <STRING>
}
```

### Classifications

Grab all available classifications.

*Response*

```json
[
    <STRING>,
    <STRING>,
    <STRING>
]
```

### File Types

Grab all defined file types.

*Response*

```json
[
    {
        "description": <STRING>,
        "extension": <STRING>,
        "type": <STRING>
    },
    {
        "description": <STRING>,
        "extension": <STRING>,
        "type": <STRING>
    }
]
```

### File Types Documents Only

Grab all document types.

*Response*

```json
[
    {
        "description": <STRING>,
        "extension": [
            <STRING>,
            <STRING>
        ],
        "type": <STRING>
    },
    {
        "description": <STRING>,
        "extension": [
            <STRING>,
            <STRING>
        ],
        "type": <STRING>
    }
]
```

### Find Matching

Search for matching files in the index.

*Headers*

- `authorization`: Authorization token.

*Params*

- `pointer`: the unique pointer for the file.
- `count`: the maximum number of results.

*Response*

```json
[
    {
        "unique_pointer": <STRING>,
        "field-1": <STRING>,
        "score": <FLOAT>
    },
    {
        "unique_pointer": <STRING>,
        "field-1": <STRING>,
        "score": <FLOAT>
    }
]
```

### Searchable Fields

Get all searchable fields.

*Response*

```json
[
    <STRING>,
    <STRING>,
    <STRING>
]
```
