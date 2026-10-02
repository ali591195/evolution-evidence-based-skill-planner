import jwt as pyjwt
import psycopg

from app.auth import create_token, decode_token, hash_password, verify_password
from app.services import user_service


class EmailTaken(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class InvalidToken(Exception):
    pass


def signup(name: str, email: str, password: str) -> dict:
    email = email.lower()
    try:
        user_id = user_service.create_user(name, email, hash_password(password))
    except psycopg.errors.UniqueViolation:
        raise EmailTaken()
    return {"id": user_id, "name": name, "email": email}


def login(email: str, password: str) -> dict:
    user = user_service.get_by_email(email.lower())
    if not user or not verify_password(password, user["password_hash"]):
        raise InvalidCredentials()
    return {"access_token": create_token(user["id"]), "token_type": "bearer"}


def user_from_token(token: str) -> dict:
    try:
        payload = decode_token(token)
    except pyjwt.PyJWTError:
        raise InvalidToken()
    user = user_service.get_by_id(payload["sub"])
    if not user:
        raise InvalidToken()
    return user