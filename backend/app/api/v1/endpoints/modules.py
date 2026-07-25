from fastapi import APIRouter, Depends

from app.dependencies.auth import require_roles
from app.models.user import User, UserRole

router = APIRouter()


@router.get("", summary="List available modules")
def list_modules(_: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER))) -> list[dict[str, str]]:
    return [
        {"name": "dashboard", "title": "Dashboard"},
        {"name": "orders", "title": "Zakázky"},
        {"name": "customers", "title": "Zákazníci"},
        {"name": "technicians", "title": "Technici"},
        {"name": "calendar", "title": "Kalendář"},
        {"name": "documents", "title": "Dokumenty"},
        {"name": "settings", "title": "Nastavení"},
    ]
