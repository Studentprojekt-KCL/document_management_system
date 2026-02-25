# Embedded Ranker Service

## Description
This microservice provides semantic document ranking using Cross-Encoder models. It is used to evaluate the relevance of document content against a specific query to refine search accuracy.

## Environment Setup
Before running the service, you must create a `.env` file in the root directory. The application will not start without these variables. 

Create a `.env` file based on this structure:

```env
# Infrastructure setup
HOST=0.0.0.0
PORT=8000

# Model configuration
MODEL_NAME=BAAI/bge-reranker-v2-m3
```

## Running the Service locally
To build and run the service via Docker:

1. **Build the image:**
   ```bash
   sudo docker build -t stochastic-analyzer .
   ```
2. **Run the container (injecting the .env file):**
   ```bash
   sudo docker run --env-file .env -p 8000:8000 stochastic-analyzer
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
  "device": "GPU"
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