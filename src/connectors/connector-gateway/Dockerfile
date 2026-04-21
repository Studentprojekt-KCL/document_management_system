FROM python:3.13-slim-trixie

COPY src/connectors/connector-gateway /src/connector-gateway/
COPY src/shared_functions /src/shared_functions

WORKDIR /src/connector-gateway

RUN python -m pip install build
RUN python -m build
RUN python -m pip install .

ENTRYPOINT ["connector_gateway"]
