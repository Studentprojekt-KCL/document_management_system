FROM python:3.13-slim

WORKDIR /app

COPY src/shared_functions/ src/shared_functions/
COPY src/stochastic_analyzer_v2/ src/stochastic_analyzer/

RUN pip install --no-cache-dir ./src/stochastic_analyzer/

ENTRYPOINT ["gateway"]
