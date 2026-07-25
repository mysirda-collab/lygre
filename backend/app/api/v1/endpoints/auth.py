from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, LogoutRequest, RefreshRequest, TokenPairResponse, UserSummary
from app.services.auth_service import authenticate_user, issue_token_pair, logout_refresh_token, refresh_access_token

router = APIRouter()


@router.post("/login", response_model=TokenPairResponse, summary="Login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    user = authenticate_user(db, payload.email, payload.password)
    access_token, refresh_token, expires_in = issue_token_pair(db, user)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserSummary.model_validate(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse, summary="Refresh access token")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    _, access_token, expires_in = refresh_access_token(db, payload.refresh_token)
    return AccessTokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=204, summary="Logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    logout_refresh_token(db, payload.refresh_token)


@router.get("/me", response_model=UserSummary, summary="Current user")
def me(current_user: User = Depends(get_current_user)) -> UserSummary:
    return UserSummary.model_validate(current_user)
