# Builder
FROM python:3.13.13-alpine3.23 AS builder

WORKDIR /build

COPY src/connectors/connector-gateway /build/connectors/connector-gateway
COPY src/shared_functions /build/shared_functions

RUN python -m pip install --upgrade pip build \
 && python -m build /build/connectors/connector-gateway

# Runner 
FROM python:3.13.13-alpine3.23

RUN addgroup -S appgroup \
 && adduser -S appuser -G appgroup \
 && mkdir -p /app \
 && chown -R appuser:appgroup /app

WORKDIR /app

COPY --from=builder /build/shared_functions/ /tmp/shared_functions/
COPY --from=builder /build/connectors/connector-gateway/dist/*.whl /tmp/connectors/connector-gateway/

RUN python -m pip install --no-cache-dir \
 /tmp/connectors/connector-gateway/*.whl \
 && rm -rf /tmp/connectors/connector-gateway \
 && rm -rf /tmp/shared_functions

USER appuser
ENTRYPOINT ["connector_gateway"]
