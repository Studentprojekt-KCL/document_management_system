FROM python:3.13-trixie AS build
COPY . /src/
COPY ./pyproject.toml /src/
WORKDIR /src
RUN python -m pip install build
RUN python -m build

FROM python:3.13-trixie AS install
COPY --from=build /src/dist/search_engine-*.whl /src/
WORKDIR /src
RUN python -m pip install search_engine-*.whl
ENTRYPOINT ["search_engine"]
