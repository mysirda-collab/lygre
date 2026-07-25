from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    TokenKind,
    create_access_token,
    create_refresh_token,
    decode_token_safe,
    hash_password,
    hash_token,
    verify_password,
)
from app.crud.refresh_token import create_refresh_token as create_refresh_token_record
from app.crud.refresh_token import get_refresh_token, revoke_refresh_token
from app.crud.user import create_user, get_user_by_email
from app.models.user import ROLE_VALUES, User, UserRole


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return user


def issue_token_pair(db: Session, user: User) -> tuple[str, str, int]:
    access_token, expires_in = create_access_token(user_id=user.id, role=user.role)
    refresh_token, refresh_expires_at = create_refresh_token(user_id=user.id)
    create_refresh_token_record(
        db,
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires_at,
    )
    return access_token, refresh_token, expires_in


def refresh_access_token(db: Session, refresh_token: str) -> tuple[User, str, int]:
    payload = decode_token_safe(refresh_token)
    if not payload or payload.get("type") != TokenKind.REFRESH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    token_record = get_refresh_token(db, hash_token(refresh_token))
    if not token_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")

    now = datetime.now(UTC)
    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if token_record.revoked_at is not None or expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    user = token_record.user_id and db.get(User, token_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or not found")

    access_token, expires_in = create_access_token(user_id=user.id, role=user.role)
    return user, access_token, expires_in


def logout_refresh_token(db: Session, refresh_token: str) -> None:
    token_record = get_refresh_token(db, hash_token(refresh_token))
    if token_record:
        revoke_refresh_token(db, token_record)


def seed_admin_user(db: Session, *, email: str, full_name: str, password: str) -> User:
    existing = get_user_by_email(db, email)
    if existing:
        return existing
    password_hash = hash_password(password)
    return create_user(
        db,
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        role=UserRole.ADMIN,
        is_active=True,
    )


def validate_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in ROLE_VALUES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    return normalized
