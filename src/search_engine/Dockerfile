FROM python:3.13-alpine
COPY src/search_engine /src/search_engine/
COPY src/shared_functions /src/shared_functions
WORKDIR /src/search_engine
RUN apk add cargo; python -m pip install build; python -m build; python -m pip install .

ENTRYPOINT ["se_api"]
