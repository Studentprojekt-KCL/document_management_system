FROM python:3.13-slim

# Fallback port only when the runtime does not set CONFLUENCE_CONNECTOR_PORT (e.g. some CI previews).
# Override per environment in compose/deploy secrets — use the port agreed for that stack, not necessarily 8010.
ENV CONFLUENCE_CONNECTOR_PORT=8010

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/confluence ./connectors/confluence

WORKDIR /app/connectors/confluence

RUN pip install --upgrade pip
RUN pip install .

CMD ["confluence_connector"]
