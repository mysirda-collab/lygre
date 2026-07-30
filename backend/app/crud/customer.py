from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_customer(db: Session, *, uuid: str, customer_number: str, name: str, phone: str | None = None, email: str | None = None, street: str | None = None, city: str | None = None, zip: str | None = None) -> Customer:
    customer = Customer(
        uuid=uuid,
        customer_number=customer_number,
        name=name,
        phone=phone,
        email=email,
        street=street,
        city=city,
        zip=zip,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(db: Session, customer: Customer, **kwargs) -> Customer:
    for k, v in kwargs.items():
        setattr(customer, k, v)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer_by_id(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def get_customer_by_number(db: Session, customer_number: str) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.customer_number == customer_number))


def find_by_phone(db: Session, phone: str) -> Sequence[Customer]:
    return db.scalars(select(Customer).where(Customer.phone == phone)).all()


def search_customers(db: Session, *, query: str, limit: int = 20) -> Sequence[Customer]:
    q = f"%{query}%"
    filters = [Customer.name.ilike(q), Customer.customer_number.ilike(q), Customer.phone.ilike(q)]
    normalized_phone = "".join(character for character in query if character.isdigit())
    if len(normalized_phone) == 12 and normalized_phone.startswith("420"):
        normalized_phone = normalized_phone[3:]
    if len(normalized_phone) == 9:
        normalized_phone_column = Customer.phone
        for separator in (" ", "+", "-", "(", ")", ".", "/"):
            normalized_phone_column = func.replace(normalized_phone_column, separator, "")
        filters.append(normalized_phone_column.like(f"%{normalized_phone}"))
    return db.scalars(select(Customer).where(or_(*filters)).limit(limit)).all()


def find_or_create(db: Session, *, uuid: str | None, customer_number: str | None, name: str | None, phone: str | None = None, email: str | None = None, street: str | None = None, city: str | None = None, zip: str | None = None) -> Customer:
    if customer_number:
        existing = get_customer_by_number(db, customer_number)
        if existing:
            return existing
    if phone:
        matches = find_by_phone(db, phone)
        if len(matches) == 1:
            return matches[0]

    # create new customer
    import uuid as _uuid

    cid = _uuid.uuid4().hex if not uuid else uuid
    return create_customer(db, uuid=cid, customer_number=customer_number or f"AUTO-{cid}", name=name or "", phone=phone, email=email, street=street, city=city, zip=zip)


def merge_customers(db: Session, primary: Customer, source: Customer) -> Customer:
    """Merge source into primary: reassign jobs and reservations, then delete source."""
    # reassign jobs
    from app.models.job import Job
    from app.models.reservation import Reservation

    db.query(Job).filter(Job.customer_id == source.id).update({"customer_id": primary.id})
    # reassign reservations if model exists
    try:
        db.query(Reservation).filter(Reservation.customer_id == source.id).update({"customer_id": primary.id})
    except Exception:
        pass
    # delete source customer
    db.delete(source)
    db.commit()
    db.refresh(primary)
    return primary
