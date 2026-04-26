# Builder
FROM python:3.13.13-slim-trixie AS builder

RUN pip install --upgrade pip build

COPY src/connectors/connector-gateway/pyproject.toml /build/connectors/connector-gateway/
COPY src/connectors/connector-gateway/setup.py /build/connectors/connector-gateway/
COPY src/connectors/connector-gateway/src/ /build/connectors/connector-gateway/src/

COPY src/shared_functions/pyproject.toml /build/shared_functions/
COPY src/shared_functions/src/ /build/shared_functions/src/

RUN python -m build /build/connectors/connector-gateway
RUN pip install /build/connectors/connector-gateway 

# Runner 
FROM gcr.io/distroless/python3-debian13:nonroot

WORKDIR /home/nonroot

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/connector_gateway /usr/local/bin/connector_gateway

ENV PYTHONPATH="/usr/local/lib/python3.13/site-packages"

# I know this is ugly but but it's a huge hassle to fix linking from /usr/local/bin/python3.13 -> /usr/bin/python
ENTRYPOINT ["python", "/usr/local/bin/connector_gateway"]
