FROM python:3.13-slim

# Override per environment in compose/deploy — defaults match local/preview stacks.
ENV CONFLUENCE_BIND_ADDR=0.0.0.0
# Fallback port only when the runtime does not set CONFLUENCE_BIND_PORT (e.g. some CI previews).
ENV CONFLUENCE_BIND_PORT=8010

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/confluence ./connectors/confluence

WORKDIR /app/connectors/confluence

RUN pip install --upgrade pip
RUN pip install .

CMD ["confluence_connector"]
