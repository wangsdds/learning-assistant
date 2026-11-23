import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.schemas import LoginIn, UserCreate, UserOut
from app.security import create_access_token, get_current_user


router = APIRouter(tags=["users"])


@router.post("/login")
def login(payload: LoginIn, session: Session = Depends(get_session)):
    user = session.scalar(select(User).where(User.email == payload.email))
    if user is None:
        raise HTTPException(status_code=401, detail="invalid email or password")
    if not bcrypt.checkpw(
        payload.password.encode("utf-8"),
        user.password.encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="invalid email or password")
    return {
        "access_token": create_access_token(user.user_id),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, session: Session = Depends(get_session)):
    hashed = bcrypt.hashpw(
        payload.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    user = User(email=payload.email, nickname=payload.nickname, password=hashed)
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="email already registered")
    return user


@router.get("/users/by-email/{email}", response_model=UserOut)
def get_email(
    email: str,
    current_user: User = Depends(get_current_user),
):
    if email.lower() != current_user.email.lower():
        raise HTTPException(status_code=404, detail="user not found")
    return current_user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="user not found")
    return current_user
