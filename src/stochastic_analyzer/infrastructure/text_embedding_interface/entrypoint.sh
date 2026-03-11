#!/bin/bash
set -e

MODEL_ID="BAAI/bge-reranker-v2-m3"

huggingface-cli download "$MODEL_ID" --cache-dir /data

exec text-embeddings-router \
    --model-id "$MODEL_ID" \
    --port 80 \
    --pooling cls