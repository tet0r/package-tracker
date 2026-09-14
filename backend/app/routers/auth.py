from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import auth
from ..db import get_db

router = APIRouter()


class Credentials(BaseModel):
    username: str
    password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        auth.SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=auth.SESSION_TTL_DAYS * 86400,
    )


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return {"setup_required": auth.setup_required(db)}


@router.post("/setup")
def setup(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    if not auth.setup_required(db):
        raise HTTPException(403, "Setup already completed")
    username = payload.username.strip()
    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if len(payload.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user = auth.create_user(db, username, payload.password)
    token = auth.create_session(db, user)
    _set_session_cookie(response, token)
    return {"username": user.username}


@router.post("/login")
def login(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    user = auth.authenticate(db, payload.username.strip(), payload.password)
    if user is None:
        raise HTTPException(401, "Invalid username or password")
    token = auth.create_session(db, user)
    _set_session_cookie(response, token)
    return {"username": user.username}


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if session_token:
        auth.delete_session(db, session_token)
    response.delete_cookie(auth.SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(user=Depends(auth.get_current_user)):
    return {"username": user.username}


@router.post("/change-password")
def change_password(
    payload: ChangePassword,
    response: Response,
    user=Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    user.password_hash = auth.hash_password(payload.new_password)
    db.commit()
    auth.delete_all_sessions_for_user(db, user.id)
    token = auth.create_session(db, user)
    _set_session_cookie(response, token)
    return {"ok": True}
