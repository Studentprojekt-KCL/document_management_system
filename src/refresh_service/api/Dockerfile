# Builder
FROM python:3.13.13-slim-trixie AS builder

RUN pip install --upgrade pip build

COPY src/refresh_service/api/pyproject.toml /build/refresh_service/api/
COPY src/refresh_service/api/setup.py /build/refresh_service/api/
COPY src/refresh_service/api/src/ /build/refresh_service/api/src/

COPY src/shared_functions/pyproject.toml /build/shared_functions/
COPY src/shared_functions/src/ /build/shared_functions/src/

RUN python -m build /build/refresh_service/api
RUN pip install /build/refresh_service/api

# Runner 
FROM gcr.io/distroless/python3-debian13:nonroot

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/refresh-service /usr/local/bin/refresh-service
COPY --from=builder /usr/local/bin/refresh-worker /usr/local/bin/refresh-worker
