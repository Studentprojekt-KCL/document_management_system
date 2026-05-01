FROM python:3.13-slim-trixie
COPY src/search_engine /src/search_engine/
COPY src/shared_functions /src/shared_functions
WORKDIR /src/search_engine
RUN apt update
RUN apt install -y ffmpeg
RUN python -m pip install build
RUN python -m build
RUN python -m pip install .

ENTRYPOINT ["se_api"]
