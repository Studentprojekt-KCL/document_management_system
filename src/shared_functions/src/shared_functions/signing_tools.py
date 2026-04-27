"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import base64
import hashlib
import hmac
import json

from shared_functions.dmis_logger import dms_info


def _b64url_encode(data: bytes) -> str:
    """Base64 encode bytes."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    """Base64 decode bytes."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(data: bytes, secret_key: bytes) -> str:
    """Generate base64 encoded HMAC signature of data using secret_key."""
    signature = hmac.new(secret_key, data, hashlib.sha256).digest()
    return _b64url_encode(signature)


def sign_encode_state(payload: dict, secret_key: str) -> str:
    """Base64 encode state and sign with secret_key.

    Returns:
    -------
        Structure: 'encoded_payload:signature'
    """
    raw = json.dumps(payload).encode()
    encoded = _b64url_encode(raw)
    signature = _sign(encoded.encode(), bytes(secret_key, "utf-8"))
    return f"{encoded}:{signature}"


def validate_decode_state(state: str, secret_key: str) -> tuple[bool, dict]:
    """Validate signed payload.

    Args:
    ----
        state: Date with structure 'encoded_payload:signature'
        secret_key: Secret key payload was signed with.
    """
    try:
        encoded, signature = state.split(":")
    except ValueError:
        dms_info(f"An invalid request was made to validate_decode_state method: {state}")
        return False, {}

    expected_sig = _sign(encoded.encode(), bytes(secret_key, "utf-8"))

    if hmac.compare_digest(signature, expected_sig):
        payload_bytes = _b64url_decode(encoded)
        return True, json.loads(payload_bytes)

    dms_info(f"A request with a tampered signature was sent to validate_decode_state method: {state}")
    return False, {}
