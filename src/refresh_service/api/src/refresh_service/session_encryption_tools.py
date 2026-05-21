"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import json
import os
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class SessionEncryption:
    """Tools for encrypting and decrypting session variables."""

    def __init__(self, secret_key: str) -> None:
        """Constructor."""
        self.suite = self._generate_suite(secret_key)

    @staticmethod
    def _generate_suite(secret_key: str) -> Fernet:
        """Generate Fernet suite with secret key."""
        raw_salt = os.environ.get("REFSERVICE_ENC_SALT", "")
        # Salt must be set in the environment; a missing salt weakens key derivation.
        salt = raw_salt.encode() if raw_salt else b"STATIC_SALT"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        encoded_key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return Fernet(encoded_key)

    def encrypt_session_vars(self, session_vars: dict) -> str:
        """Cast given dictionary into str and return encrypted string."""
        session_str = json.dumps(session_vars)
        raw_string = session_str.encode()
        return self.suite.encrypt(raw_string).decode("utf-8")

    def decrypt_session_variables(self, encrypted_str: str) -> dict:
        """Decrypt session variables."""
        encrypted_bytes = bytes(encrypted_str, "utf-8")
        return json.loads(self.suite.decrypt(encrypted_bytes).decode())
