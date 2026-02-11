FROM python:3.13-trixie as build
COPY ./src/ /src/
COPY ./pyproject.toml /src/
WORKDIR /src
RUN python -m pip install build
RUN python -m build

FROM python:3.13-trixie
COPY --from=build /src/dist/logging_endpoint-*.whl /src/
WORKDIR /src
RUN python -m pip install logging_endpoint-*.whl
ENTRYPOINT ["python", "-m", "logging_endpoint"]
