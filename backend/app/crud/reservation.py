from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reservation import Reservation


def list_reservations_by_customer(db: Session, customer_id: int):
    return db.scalars(select(Reservation).where(Reservation.customer_id == customer_id).order_by(Reservation.created_at.desc()).limit(20)).all()
