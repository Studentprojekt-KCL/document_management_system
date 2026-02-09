FROM python:3.13-trixie
# COPY ./src/ /src/
COPY ./requierments.txt /
RUN pip install -r /requierments.txt
WORKDIR /src
ENTRYPOINT ["fastapi", "dev", "--host", "0.0.0.0", "--port", "8000", "endpoints.py"]
