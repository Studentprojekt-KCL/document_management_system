#!/bin/bash

# Start the Ollama daemon in the background
ollama serve &
OLLAMA_PID=$!

# Continuously poll the local API until it responds with a 200 status
echo "Waiting for Ollama engine to initialize..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done

# Pull the model. If it already exists in the volume, Ollama verifies it and skips the download.
echo "Verifying ministral-3:14b model status..."
ollama pull ministral-3:14b

echo "Model ready. Serving API..."
wait $OLLAMA_PID
