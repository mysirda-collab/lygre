from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.dependencies.database import get_db
from app.crud.customer import create_customer, get_customer_by_id, get_customer_by_number, update_customer, search_customers, find_or_create
from app.crud.customer import merge_customers
from app.crud.reservation import list_reservations_by_customer
from app.dependencies.auth import require_roles
from app.models.user import UserRole
import uuid as _uuid

router = APIRouter()


@router.post("", response_model=CustomerRead)
def create_customer_endpoint(payload: CustomerCreate, db: Session = Depends(get_db), _: None = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))):
    cid = _uuid.uuid4().hex
    existing = get_customer_by_number(db, payload.customer_number)
    if existing:
        raise HTTPException(status_code=400, detail="customer_number already exists")
    created = create_customer(db, uuid=cid, customer_number=payload.customer_number, name=payload.name, phone=payload.phone, email=payload.email, street=payload.street, city=payload.city, zip=payload.zip)
    return created


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer_endpoint(customer_id: int, db: Session = Depends(get_db), _: None = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER))):
    c = get_customer_by_id(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="not found")
    return c


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer_endpoint(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db), _: None = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))):
    c = get_customer_by_id(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="not found")
    updated = update_customer(db, c, **payload.model_dump())
    return updated


@router.get("", response_model=List[CustomerRead])
def search_customers_endpoint(q: str | None = None, db: Session = Depends(get_db), _: None = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER))):
    if not q:
        return []
    results = search_customers(db, query=q)
    return results


@router.get("/{customer_id}/reservations", response_model=List[dict])
def list_customer_reservations(customer_id: int, db: Session = Depends(get_db), _: None = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER))):
    items = list_reservations_by_customer(db, customer_id)
    return items


@router.post("/{primary_id}/merge", response_model=CustomerRead)
def merge_customers_endpoint(primary_id: int, payload: dict, db: Session = Depends(get_db), _: None = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))):
    source_id = payload.get("source_id")
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id required")
    primary = get_customer_by_id(db, primary_id)
    if not primary:
        raise HTTPException(status_code=404, detail="primary not found")
    source = get_customer_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    merged = merge_customers(db, primary, source)
    return merged
