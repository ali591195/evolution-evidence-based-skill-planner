from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import current_user
from app.schemas.auth import LoginIn, SignupIn
from app.services import auth_service

router = APIRouter()


@router.post("/signup", status_code=201)
def signup(body: SignupIn):
    try:
        return auth_service.signup(body.name, body.email, body.password)
    except auth_service.EmailTaken:
        raise HTTPException(status_code=409, detail="Email already registered")


@router.post("/login")
def login(body: LoginIn):
    try:
        return auth_service.login(body.email, body.password)
    except auth_service.InvalidCredentials:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user