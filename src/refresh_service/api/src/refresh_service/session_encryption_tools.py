"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import json

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

class SessionEncryption:

    suite: Fernet

    def __init__(self, secret_key: str):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'STATIC_SALT',
            iterations=100000,
        )

        encoded_key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        self.suite = Fernet(encoded_key)

    def encrypt_session_vars(self, session_vars: dict):
        session_str = json.dumps(session_vars)
        raw_string = session_str.encode()
        return self.suite.encrypt(raw_string)

    def decrypt_session_vars(self, encrypted_bytes: bytes):
        return self.suite.decrypt(encrypted_bytes).decode()
