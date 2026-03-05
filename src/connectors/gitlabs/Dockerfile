FROM python:3.12-slim

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/gitlabs ./connectors/gitlabs

WORKDIR /app/connectors/gitlabs

RUN pip install --upgrade pip
RUN pip install .

CMD ["gitlab_connector"]
