FROM python:3.13-slim

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/lorem ./connectors/lorem

WORKDIR /app/connectors/lorem

RUN pip install --upgrade pip
RUN pip install .

CMD ["lorem_connector"]
