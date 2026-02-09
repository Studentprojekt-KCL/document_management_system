FROM python:3.13-trixie
# COPY ./src/ /src/
RUN pip install "fastapi[standard]"
WORKDIR /src
ENTRYPOINT ["fastapi", "dev", "--host", "0.0.0.0", "--port", "8000", "main.py"]
