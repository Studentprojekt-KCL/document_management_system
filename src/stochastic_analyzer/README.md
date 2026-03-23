# Unified Document Analysis Gateway

## Description

This microservice provides semantic document ranking using Cross-Encoder models, alongside document security classification and batch summarization powered by generative LLMs. It evaluates the relevance of document content against a specific query, determines corporate security levels, synthesizes unified summaries from multiple sources, and converts markdown summaries to PDF.

## Developer Instructions

Run the gateway locally in developer mode, inside a virtual python environment do the following:

```bash
$ pip install -e .
$ gateway --dev
```

## Configuration

Configuration is done through environment variables.

- `BIND` — Address to bind to.
- `PORT` — Port to host on.
- `TEI_URL` — URL for the TEI reranker container.
- `CLASSIFIER_URL` — URL for the TEI classifier container.
- `MINISTRAL_URL` — URL for the Ministral LLM container.
- `MINISTRAL_MODEL` — Model identifier for Ministral.
- `DEVICE` — Compute device identifier (optional, defaults to `external`).

Optional flags:

- `--dev`, developer mode (enables debug logging and detailed error responses).

## Running the Service

To build and run the service via Docker:

1. **Build the image:**
   ```bash
   sudo docker build -t stochastic-analyzer -f src/stochastic_analyzer/Dockerfile .
   ```

2. **Run the container (using host networking):**
   ```bash
   sudo docker run -d \
     --name analyzer \
     --network host \
     --env-file src/stochastic_analyzer/.env \
     stochastic-analyzer
   ```

## Test request to API

To test that the API is working correctly, test the following CURL command:

```bash
curl -v http://127.0.0.1:8000/health
```

Which should result in a `200` and:

```json
{
  "status": "active",
  "model_loaded": true,
  "device": "external"
}
```

## API Endpoints

### 1. Health Check

Checks if the API is active and identifies the compute device.

* **URL:** `/health`
* **Method:** `GET`
* **Success Response:** `200 OK`

**Response Example:**
```json
{
  "status": "active",
  "model_loaded": true,
  "device": "external"
}
```

### 2. Document Re-Ranker

Scores and sorts a list of documents based on their semantic relevance to a provided query.

* **URL:** `/rerank`
* **Method:** `POST`
* **Content-Type:** `application/json`

**Request Body Example:**
```json
{
  "query": "What are the rules for data compliance?",
  "documents": [
    {
      "title": "GDPR Overview",
      "owner": "Legal Dept",
      "reference": "doc-001",
      "content": "General Data Protection Regulation guidelines..."
    },
    {
      "title": "Lunch Menu",
      "owner": "HR",
      "reference": "doc-002",
      "content": "Today we are serving meatballs..."
    }
  ]
}
```

**Success Response:** `200 OK`

**Response Example:**
```json
{
  "ranked_results": [
    {
      "score": 0.892,
      "document": {
        "title": "GDPR Overview",
        "owner": "Legal Dept",
        "reference": "doc-001",
        "content": "General Data Protection Regulation guidelines..."
      }
    },
    {
      "score": -1.245,
      "document": {
        "title": "Lunch Menu",
        "owner": "HR",
        "reference": "doc-002",
        "content": "Today we are serving meatballs..."
      }
    }
  ]
}
```

### 3. Document Classifier

Classifies documents into security levels (Public, Internal, Sensitive, Confidential) using zero-shot NLI inference via the RoBERTa TEI container.

* **URL:** `/classify`
* **Method:** `POST`
* **Content-Type:** `application/json`

**Request Body Example:**
```json
[
  {
    "content": "Quarterly financial projections and unreleased earnings targets.",
    "metadata": {
      "name": "Q3_Projections",
      "author": "Finance Team"
    }
  }
]
```

**Success Response:** `200 OK`

**Response Example:**
```json
[
  {
    "name": "Q3_Projections",
    "Security-class": "Confidential"
  }
]
```

### 4. Batch Summarizer

Synthesizes the content of multiple documents into a single, unified summary using the Ministral model.

* **URL:** `/summarize`
* **Method:** `POST`
* **Content-Type:** `application/json`

**Request Body Example:**
```json
[
  {
    "content": "Quarterly financial projections and unreleased earnings targets.",
    "metadata": {
      "name": "Q3_Projections",
      "author": "Finance Team"
    }
  },
  {
    "content": "Marketing expenditure was reduced by 15% across European regions.",
    "metadata": {
      "name": "EU_Marketing_Q3",
      "author": "Marketing Team"
    }
  }
]
```

**Success Response:** `200 OK`

**Response Example:**
```json
{
  "summary": "In Q3, the organization focused on strict financial projections and unreleased earnings targets, alongside a 15% reduction in European marketing expenditure."
}
```

### 5. Markdown to PDF

Converts a markdown summary into a downloadable PDF file.

* **URL:** `/md-to-pdf`
* **Method:** `POST`
* **Content-Type:** `application/json`

**Request Body Example:**
```json
{
  "summary": "# Incident Summary\n\nThe servers experienced downtime at 2 AM due to a power outage. No data loss was reported."
}
```

**Success Response:** `200 OK` with `application/pdf` body.

**CURL Example:**
```bash
curl -X POST http://localhost:8000/md-to-pdf \
  -H "Content-Type: application/json" \
  -d '{"summary": "# Report\n\nThis is the summary content."}' \
  --output summary.pdf
```

## Further API documentation

An automated API documentation is constructed when the API service is started, and can be found at http://127.0.0.1:8000/docs
