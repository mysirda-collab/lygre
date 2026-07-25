from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.dependencies.database import get_db
from app.crud.customer import create_customer, get_customer_by_id, get_customer_by_number, update_customer, search_customers, find_or_create
import uuid as _uuid

router = APIRouter()


@router.post("", response_model=CustomerRead)
def create_customer_endpoint(payload: CustomerCreate, db: Session = Depends(get_db)):
    cid = _uuid.uuid4().hex
    existing = get_customer_by_number(db, payload.customer_number)
    if existing:
        raise HTTPException(status_code=400, detail="customer_number already exists")
    created = create_customer(db, uuid=cid, customer_number=payload.customer_number, name=payload.name, phone=payload.phone, email=payload.email, street=payload.street, city=payload.city, zip=payload.zip)
    return created


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer_endpoint(customer_id: int, db: Session = Depends(get_db)):
    c = get_customer_by_id(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="not found")
    return c


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer_endpoint(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    c = get_customer_by_id(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="not found")
    updated = update_customer(db, c, **payload.model_dump())
    return updated


@router.get("", response_model=List[CustomerRead])
def search_customers_endpoint(q: str | None = None, db: Session = Depends(get_db)):
    if not q:
        return []
    results = search_customers(db, query=q)
    return results
