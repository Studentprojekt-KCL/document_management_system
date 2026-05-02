FROM python:3.13-slim-trixie

COPY src/search_engine/src /src/search_engine/src
COPY src/search_engine/pyproject.toml /src/search_engine/pyproject.toml
COPY src/search_engine/setup.py /src/search_engine/setup.py

COPY src/shared_functions/src /src/shared_functions/src
COPY src/shared_functions/pyproject.toml /src/shared_functions/pyproject.toml

WORKDIR /src/search_engine
RUN python -m pip install build
RUN python -m build
RUN python -m pip install .

ENTRYPOINT ["se_api"]
