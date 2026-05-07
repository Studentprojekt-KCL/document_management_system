FROM python:3.13-slim

ENV CONFLUENCE_CONNECTOR_PORT=8010

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/confluence ./connectors/confluence

WORKDIR /app/connectors/confluence

RUN pip install --upgrade pip
RUN pip install .

CMD ["confluence_connector"]
