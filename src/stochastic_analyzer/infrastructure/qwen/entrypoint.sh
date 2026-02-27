ollama serve &
OLLAMA_PID=$!

# Continuously poll the local API until it responds with a 200 status
echo "Waiting for Ollama engine to initialize..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done

# Pull the Qwen model. If it already exists in the volume, Ollama verifies it and skips the download.
echo "Verifying qwen2.5:0.5b model status..."
ollama pull qwen2.5:0.5b

echo "Model ready. Serving API..."
wait $OLLAMA_PID