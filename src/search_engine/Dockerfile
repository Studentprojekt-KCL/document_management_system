FROM python:3.13-trixie AS build
COPY . /src/
COPY ./pyproject.toml /src/
WORKDIR /src
RUN python -m pip install build
RUN python -m build

FROM python:3.13-trixie AS install
COPY --from=build /src/dist/se_api-*.whl /src/
WORKDIR /src
RUN python -m pip install se_api-*.whl
ENTRYPOINT ["se_api"]
