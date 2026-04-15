FROM python:3.13-slim-trixie
COPY src/search_engine /src/search_engine/
COPY src/shared_functions /src/shared_functions
WORKDIR /src/search_engine
RUN python -m pip install build; python -m build; python -m pip install .

ENTRYPOINT ["se_api"]
