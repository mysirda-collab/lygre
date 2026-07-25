from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


def create_refresh_token(
    db: Session,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_refresh_token(db: Session, token_hash: str) -> RefreshToken | None:
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))


def revoke_refresh_token(db: Session, token: RefreshToken) -> RefreshToken:
    token.revoked_at = datetime.now(UTC)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def revoke_all_user_tokens(db: Session, user_id: int) -> None:
    active_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ).all()
    now = datetime.now(UTC)
    for token in active_tokens:
        token.revoked_at = now
        db.add(token)
    db.commit()
