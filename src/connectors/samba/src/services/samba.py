"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import uuid
import logging
from dmis_logger import dms_warning
from smbprotocol import exceptions
from smbprotocol.connection import Connection, SMBConnectionClosed, SMBException
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from initialisation_tools import read_env_variable, read_port

from smbprotocol.open import (
    CreateDisposition,
    CreateOptions,
    DirectoryAccessMask,
    FileAttributes,
    FileInformationClass,
    FilePipePrinterAccessMask,
    ImpersonationLevel,
    Open,
    ShareAccess,
)

class Samba:
    """Service for the Samba contection.

    Variables:
        host: string containing the host of the SMB share.
        share: name of the share.
        user: user to access the share with.
        password: user password.
        path: where to mount the share.
    """

    host: str
    port: int
    share: str
    user: str
    password: str

    def __init__(self) -> None:
        """Constructor."""
        self.host = read_env_variable("SC_SAMBA_HOST")
        self.port = read_port("SC_SAMBA_PORT")
        self.share = rf"\\{self.host}\{read_env_variable("SC_SAMBA_SHARE")}"
        self.user = read_env_variable("SC_SAMBA_USER")
        self.password = read_env_variable("SC_SAMBA_PASS")

    def connect(self):
        logging.getLogger('smbprotocol').setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger('smbprotocol').addHandler(handler)

        connection = Connection(uuid.uuid4(), self.host, self.port)
        connection.connect()
        try:
            session = Session(connection, username=self.user, password=self.password)
            session.connect()
            if session.session_id is not None:
                print(connection.echo(sid=session.session_id))
            print(self.share)
            tree = TreeConnect(session, self.share)
            tree.connect()
            dir_open = Open(tree, ".")
            compound_messages = [
                dir_open.query_directory("*", FileInformationClass.FILE_NAMES_INFORMATION, send=False),
                dir_open.close(False, send=False),
            ]
            requests = connection.send_compound([x[0] for x in compound_messages], session.session_id, tree.tree_connect_id)
            for i, request in enumerate(requests):
                response = compound_messages[i][1](request)
                print(response)
        finally:
            connection.disconnect()



    def get_files(self, subdata: str | None) -> dict:
        """Get new files from SMB share.

        Args:
            subdata: date and tim in iso format encoded with base64, represents the newest file date.
        Return: Dict containting a list of file pointers and subdata.

        """

        connection = Connection(uuid.uuid4(), self.host, self.port, False)
        connection.connect()
        try:
            session = Session(connection, self.user, self.password, require_encryption=False)
            session.connect()
            tree = TreeConnect(session, self.share)
            tree.connect()
            # dir_open = Open(tree, "Kernel")
            # compound_messages = [
            #     dir_open.query_directory("*", FileInformationClass.FILE_NAMES_INFORMATION, send=False),
            #     dir_open.close(False, send=False),
            # ]
            # requests = connection.send_compound([x[0] for x in compound_messages], session.session_id, tree.tree_connect_id)
            # for i, request in enumerate(requests):
            #     response = compound_messages[i][1](request)
            #     print(response)
        finally:
            connection.disconnect()

        return {}
