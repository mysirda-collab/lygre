import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenKind:
    ACCESS = "access"
    REFRESH = "refresh"


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(*, user_id: int, role: str) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.access_token_expires_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": TokenKind.ACCESS,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def create_refresh_token(*, user_id: int) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expires_days)
    random_part = secrets.token_urlsafe(48)
    payload = {
        "sub": str(user_id),
        "type": TokenKind.REFRESH,
        "rand": random_part,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def decode_token_safe(token: str) -> dict | None:
    try:
        return decode_token(token)
    except JWTError:
        return None
