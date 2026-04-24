FROM python:3.13-slim-trixie AS builder

WORKDIR /build

COPY src/connectors/connector-gateway /build/connectors/connector-gateway
COPY src/shared_functions /build/shared_functions

RUN python -m pip install --upgrade pip build \
 && python -m build /build/connectors/connector-gateway

# --- runtime stage ---
FROM python:3.13-slim-trixie

WORKDIR /app

COPY --from=builder /build/connectors/connector-gateway/dist/*.whl /tmp/
COPY --from=builder /build/connectors/connector-gateway/dist/*.whl /tmp/

RUN python -m pip install --no-cache-dir /tmp/*.whl \
 && rm -rf /tmp/*.whl

ENTRYPOINT ["connector_gateway"]