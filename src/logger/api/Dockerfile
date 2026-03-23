FROM python:3.13-alpine
COPY src/logger/api /src/logger/api/
COPY src/shared_functions /src/shared_functions
WORKDIR /src/logger/api
RUN python -m pip install build; python -m build; python -m pip install .
ENTRYPOINT ["log_api"]

