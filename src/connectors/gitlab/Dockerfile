FROM python:3.13-slim

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/gitlab ./connectors/gitlab

WORKDIR /app/connectors/gitlab

RUN pip install --upgrade pip
RUN pip install .

CMD ["gitlab_connector"]
