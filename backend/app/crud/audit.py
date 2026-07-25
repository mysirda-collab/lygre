from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def create_audit_log(db: Session, *, entity_type: str, entity_id: int, action: str, details: str | None = None) -> None:
    log = AuditLog(entity_type=entity_type, entity_id=entity_id, action=action, details=details)
    db.add(log)
    db.commit()
