FROM python:3.13-alpine AS build

WORKDIR /app

RUN python -m pip install --upgrade pip build

# Build shared package
COPY src/shared_functions /app/shared_functions
WORKDIR /app/shared_functions
RUN python -m build

# Build API package
COPY src/api /app/api
WORKDIR /app/api
RUN python -m build

# Runtime stage
FROM python:3.13-alpine

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY --from=build /app/shared_functions/dist/*.whl /tmp/
COPY --from=build /app/api/dist/*.whl /tmp/

RUN python -m pip install --no-cache-dir /tmp/*.whl \
    && rm -rf /tmp/*.whl

ENV PORT=8000

EXPOSE 8000

ENTRYPOINT ["dmis_api"]