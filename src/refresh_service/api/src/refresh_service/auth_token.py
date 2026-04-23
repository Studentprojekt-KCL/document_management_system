"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

#TODO, it is expected that all tokens aleardy are validated, do we want to validate them again here?

import jwt
from jwt import PyJWKClient


def authorize_and_get_token(authorization: str | None) -> tuple[bool,dict]:
        """Validate bearer token and return token claims."""
        jwks_client = PyJWKClient("https://ad.dms-lookup.com:8443/realms/master/protocol/openid-connect/certs") #TODO, this is tmp, needs to be moved.
        issuer = "https://ad.dms-lookup.com:8443/realms/master" #TODO, this is tmp, needs to be moved.

        if authorization is None:
            print(1)
            return False, {}

        scheme, _, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not token:
            print(2)
            return False, {}

        token = token.strip()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},
        )
        return True, claims