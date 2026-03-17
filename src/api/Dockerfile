FROM python:3.13-alpine AS build

WORKDIR /app

RUN pip install --upgrade pip build

# Build shared package
COPY src/shared_functions /app/shared_functions
WORKDIR /app/shared_functions
RUN python -m build

# Build API package
WORKDIR /app/api
COPY src/api/pyproject.toml /app/api/
COPY src/api/src /app/api/src
RUN python -m build

# Runtime stage
FROM python:3.13-alpine

WORKDIR /app

RUN pip install --upgrade pip

COPY --from=build /app/api/dist/*.whl /tmp/
COPY --from=build /app/shared_functions/dist/*.whl /tmp/

RUN ls -l /tmp \
    && python -m pip install --no-cache-dir /tmp/*.whl \
    && python -m pip list \
    && python -c "import dmis_api; print(dmis_api.__file__)" \
    && rm -rf /tmp/*.whl

ENTRYPOINT ["python", "-c", "from dmis_api.api import run; run()"]
