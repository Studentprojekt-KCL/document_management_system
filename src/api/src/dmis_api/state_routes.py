from typing import Any

from fastapi import Cookie, HTTPException
from fastapi.responses import JSONResponse


class StateRoutes:
    def __init__(self, token_verifier):
        self.token_verifier = token_verifier
        self.state_by_user: dict[str, dict[str, Any]] = {}

    def _response(self, content: dict[str, Any], status_code: int = 200) -> JSONResponse:
        return JSONResponse(status_code=status_code, content=content)

    def _get_user_id(self, access_token: str | None) -> str:
        if not access_token:
            raise HTTPException(status_code=401, detail="Missing access token")

        claims = self.token_verifier.verify_access_token(f"Bearer {access_token}")
        user_id = claims.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject")

        return str(user_id)

    async def get_state(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        user_id = self._get_user_id(access_token)
        return self._response({"state": self.state_by_user.get(user_id, {})})

    async def put_state(
        self,
        payload: dict[str, Any],
        access_token: str | None = Cookie(default=None),
    ) -> JSONResponse:
        user_id = self._get_user_id(access_token)
        self.state_by_user[user_id] = payload or {}
        return self._response({"message": "State saved"})

    async def delete_state(self, access_token: str | None = Cookie(default=None)) -> JSONResponse:
        user_id = self._get_user_id(access_token)
        self.state_by_user.pop(user_id, None)
        return self._response({"message": "State cleared"})