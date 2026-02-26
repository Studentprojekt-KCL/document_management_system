FROM python:3.13-slim AS build
WORKDIR /app
COPY pyproject.toml .
COPY embedded_ranker/ embedded_ranker/
COPY classification_analyzer/ classification_analyzer/
RUN python -m pip install --no-cache-dir build
RUN python -m build

FROM python:3.13-slim AS install
WORKDIR /app
COPY --from=build /app/dist/embedded_ranker-*.whl .
RUN python -m pip install --no-cache-dir embedded_ranker-*.whl
ENTRYPOINT ["reranker"]