FROM python:3.13-alpine AS build
COPY . /src
WORKDIR /src/search_engine/
RUN python -m pip install build
RUN python -m build

FROM python:3.13-alpine AS install
COPY --from=build /src/dist/se_api-*.whl /src/
WORKDIR /src
RUN python -m pip install se_api-*.whl
ENTRYPOINT ["se_api"]
