from fastapi import APIRouter

from app.api.v1.endpoints import auth, calendar, health, jobs, modules, uploads

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(modules.router, prefix="/modules", tags=["modules"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
