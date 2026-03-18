FROM python:3.13-alpine
COPY src/connectors/samba /src/connectors/samba
COPY src/shared_functions /src/shared_functions
WORKDIR /src/samba
RUN python -m pip install build; python -m build; python -m pip install .

ENTRYPOINT ["samba_connector"]
