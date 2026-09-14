import datetime
import secrets

import bcrypt
from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models
from .db import get_db

SESSION_COOKIE_NAME = "session_token"
SESSION_TTL_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def setup_required(db: Session) -> bool:
    return db.query(models.User).count() == 0


def create_user(db: Session, username: str, password: str) -> models.User:
    user = models.User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> models.User | None:
    user = db.query(models.User).filter_by(username=username).first()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, user: models.User) -> str:
    token = secrets.token_hex(32)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=SESSION_TTL_DAYS)
    db.add(models.UserSession(token=token, user_id=user.id, expires_at=expires_at))
    db.commit()
    return token


def get_user_for_token(db: Session, token: str | None) -> models.User | None:
    if not token:
        return None
    session = db.get(models.UserSession, token)
    if session is None:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
    if expires_at < datetime.datetime.now(datetime.timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return db.get(models.User, session.user_id)


def delete_session(db: Session, token: str) -> None:
    session = db.get(models.UserSession, token)
    if session is not None:
        db.delete(session)
        db.commit()


def delete_all_sessions_for_user(db: Session, user_id: int) -> None:
    db.query(models.UserSession).filter_by(user_id=user_id).delete()
    db.commit()


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> models.User:
    user = get_user_for_token(db, session_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
