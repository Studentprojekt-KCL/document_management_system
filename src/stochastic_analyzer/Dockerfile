FROM python:3.12-slim AS build
WORKDIR /app
COPY src/stochastic_analyzer/pyproject.toml .
COPY src/stochastic_analyzer/gateway/ gateway/
RUN python -m pip install --no-cache-dir build
RUN python -m build

FROM python:3.12-slim AS install
WORKDIR /app
COPY --from=build /app/dist/stochastic_analyzer-*.whl .
RUN python -m pip install --no-cache-dir stochastic_analyzer-*.whl
ENTRYPOINT ["reranker"]