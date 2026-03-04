FROM python:3.13-alpine AS build

WORKDIR /app

RUN pip install --upgrade pip build

COPY src/api/pyproject.toml .
COPY src/api/src src

RUN python -m build

# Runtime stage
FROM python:3.13-alpine

WORKDIR /app

RUN pip install --upgrade pip

COPY --from=build /app/dist/*.whl /tmp/

RUN pip install /tmp/*.whl \
    && rm -rf /tmp/*.whl

ENTRYPOINT ["dmis_api"]