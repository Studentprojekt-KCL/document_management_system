FROM python:3.13-trixie as build
COPY ./src/ /src/
COPY ./pyproject.toml /src/
WORKDIR /src
RUN python -m pip install build
RUN python -m build

FROM python:3.13-trixie
COPY --from=build /src/dist/log_api-*.whl /src/
WORKDIR /src
RUN python -m pip install log_api-*.whl
ENTRYPOINT ["log_api"]
