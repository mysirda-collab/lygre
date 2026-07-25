from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.dependencies.database import SessionLocal
from app.middleware.request_logging import RequestLoggingMiddleware
from app.services.auth_service import seed_admin_user

setup_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="ERP skeleton for installation and order management.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def startup_seed_admin() -> None:
    db: Session = SessionLocal()
    try:
        seed_admin_user(
            db,
            email=settings.seed_admin_email,
            full_name=settings.seed_admin_name,
            password=settings.seed_admin_password,
        )
    finally:
        db.close()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Lygre API is running"}
