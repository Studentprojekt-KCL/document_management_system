#!/bin/bash

ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama engine to initialize..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done

echo "Verifying qwen2.5:0.5b model status..."
ollama pull qwen2.5:0.5b

echo "Model ready. Serving API..."
wait $OLLAMA_PID