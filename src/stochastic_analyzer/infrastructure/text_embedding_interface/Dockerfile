# Use the fixed 1.6 version of TEI
FROM ghcr.io/huggingface/text-embeddings-inference:86-1.6

# Install Python, pip, and curl for robust downloading and health checks
RUN apt-get update && apt-get install -y \
    python3 python3-pip curl \
    && rm -rf /var/lib/apt/lists/*

# Install the official Hugging Face CLI (bypass system environment restrictions if needed)
RUN pip3 install --no-cache-dir huggingface_hub --break-system-packages

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]