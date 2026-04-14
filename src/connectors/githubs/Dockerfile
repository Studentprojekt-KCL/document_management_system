FROM python:3.13-slim

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/githubs ./connectors/githubs

WORKDIR /app/connectors/githubs

RUN pip install --upgrade pip
RUN pip install .

CMD ["github_connector"]
