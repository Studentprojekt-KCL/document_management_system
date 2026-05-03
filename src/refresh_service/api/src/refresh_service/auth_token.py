"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import jwt
from jwt import PyJWKClient


def authorize_and_get_token(authorization: str | None, ad_issuer: str, openid_connect_url: str) -> tuple[bool, dict]:
    """Validate bearer token and return token claims.

    Args:
        authorization: Encoded JWT.
        ad_issuer: Domain of AD issuer, (usually ending in /realms/<reals_name>).
        openid_connect: AD openID connect URL, ((usually ending in /openid-connect/certs).
    """
    jwks_client = PyJWKClient(openid_connect_url)

    if authorization is None:
        return False, {}

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return False, {}

    token = token.strip()
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except jwt.exceptions.DecodeError:
        return False, {}

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=ad_issuer,
            options={"verify_aud": False},
        )
    except jwt.exceptions.ExpiredSignatureError:
        return False, {}
    return True, claims
