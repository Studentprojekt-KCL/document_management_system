FROM python:3.12-slim

WORKDIR /app

COPY src/shared_functions ./shared_functions

COPY src/connectors/SMB ./connectors/SMB

WORKDIR /app/connectors/SMB

RUN pip install --upgrade pip
RUN pip install .

CMD ["smb_connector"]
