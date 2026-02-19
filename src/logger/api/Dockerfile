FROM python:3.13-slim-trixie AS build
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN python -m pip install build
RUN python -m build

FROM python:3.13-slim-trixie AS install
WORKDIR /app
COPY --from=build /app/dist/log_api-*.whl .
RUN python -m pip install log_api-*.whl
ENTRYPOINT ["log_api"]
