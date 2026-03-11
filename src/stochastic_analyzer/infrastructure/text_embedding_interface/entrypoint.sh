#!/bin/bash
set -e # Exit immediately if a command fails

MODEL_ID="BAAI/bge-reranker-v2-m3"

echo "========================================"
echo "1. Checking and downloading model weights"
echo "========================================"
# This uses the robust Python tool to download the model to the mounted volume.
# It handles timeouts, retries, and resumes automatically.
huggingface-cli download "$MODEL_ID" --cache-dir /data

echo "========================================"
echo "2. Starting TEI Reranker Engine"
echo "========================================"
# Start the TEI server directly
exec text-embeddings-router \
    --model-id "$MODEL_ID" \
    --port 80 \
    --pooling cls