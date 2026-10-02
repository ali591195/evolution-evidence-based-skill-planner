from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services import auth_service

bearer = HTTPBearer()


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return auth_service.user_from_token(creds.credentials)
    except auth_service.InvalidToken:
        raise HTTPException(status_code=401, detail="Invalid or expired token")