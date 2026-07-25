from app.crud.customer import create_customer, get_customer_by_number, find_by_phone
from app.models.customer import Customer

def test_create_customer(db_session):
    c = create_customer(db_session, uuid="u1", customer_number="CUST-1", name="ACME", phone="12345")
    assert c.id is not None
    fetched = get_customer_by_number(db_session, "CUST-1")
    assert fetched.id == c.id


def test_find_by_phone(db_session):
    create_customer(db_session, uuid="u2", customer_number="CUST-2", name="Two", phone="555-000")
    res = find_by_phone(db_session, "555-000")
    assert len(res) >= 1
