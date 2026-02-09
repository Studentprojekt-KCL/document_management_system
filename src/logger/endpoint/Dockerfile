FROM python:3.13-trixie
# COPY ./src/ /src/
RUN pip install "fastapi[standard]"
RUN pip install mysql-connector-python
WORKDIR /src
ENTRYPOINT ["fastapi", "dev", "--host", "0.0.0.0", "--port", "8000", "endpoints.py"]
