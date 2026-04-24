FROM python:3.13-slim

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/sharepoint ./connectors/sharepoint

WORKDIR /app/connectors/sharepoint

RUN pip install --upgrade pip
RUN pip install .

CMD ["sharepoint_connector"]
