# Unified Document Analysis Gateway

## Description
This microservice provides semantic document ranking using Cross-Encoder models, alongside document security classification and batch summarization powered by generative LLMs. It evaluates the relevance of document content against a specific query, determines corporate security levels, and synthesizes unified summaries from multiple sources.

## Environment Setup
Before running the service, you must create a `.env` file in the root directory. The application will not start without these variables. 

Create a `.env` file based on this structure:

```env
# Infrastructure setup
HOST=0.0.0.0
PORT=8000

# Model configuration
MODEL_NAME=BAAI/bge-reranker-v2-m3

# Ministral / Ollama configuration
MINISTRAL_URL=http://localhost:11434/api/generate
MINISTRAL_MODEL=ministral-3:14b

# Qwen / Ollama configuration
QWEN_URL=http://localhost:11435/api/generate
QWEN_MODEL=qwen2.5:0.5b
```

## Running the Service locally
To build and run the service via Docker:

1. **Build the image:**
   ```bash
   sudo docker build -t stochastic-analyzer .
   ```
2. **Run the container (using host networking and attaching GPUs):**
   ```bash
   sudo docker run -d --gpus all --network host --env-file .env stochastic-analyzer
   ```

## API Endpoints

### 1. Health Check
Checks if the API is active, if the model has successfully loaded into memory, and identifies the compute device.

* **URL:** `/health`
* **Method:** `GET`
* **Success Response:** `200 OK`

**Response Example:**
```json
{
  "status": "active",
  "model_loaded": true,
  "device": "cuda"
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
Analyzes document content and metadata to assign a strict security classification (Public, Internal, Sensitive, or Confidential) using the Qwen model.

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