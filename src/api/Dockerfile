FROM python:3.13-slim

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/api ./api

WORKDIR /app/api

RUN pip install --upgrade pip
RUN pip install .

CMD ["dmis_api"]
