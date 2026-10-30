import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.repositories.customer_repository import CustomerRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.ledger_repository import LedgerRepository
from app.core.exceptions import BusinessRuleViolationException


def test_customer_repository_crud(db_session: Session):
    repo = CustomerRepository(db_session)
    # Create
    c = Customer(name="John Doe", email="john@example.com")
    created = repo.create(c)
    assert created.id is not None
    assert created.email == "john@example.com"

    # Get by ID
    fetched = repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "John Doe"

    # Get by Email
    by_email = repo.get_by_email("JOHN@example.com")
    assert by_email is not None
    assert by_email.id == created.id

    # List & Count
    assert repo.count() == 1
    items = repo.list()
    assert len(items) == 1


def test_plan_repository_list_active(db_session: Session):
    repo = PlanRepository(db_session)
    active_plan = Plan(name="Active Plan", price=Decimal("10.00"), currency="USD", billing_interval="monthly", is_active=True)
    inactive_plan = Plan(name="Old Plan", price=Decimal("5.00"), currency="USD", billing_interval="monthly", is_active=False)
    repo.create(active_plan)
    repo.create(inactive_plan)

    active_items = repo.list_active()
    assert len(active_items) == 1
    assert active_items[0].name == "Active Plan"

    all_items = repo.list()
    assert len(all_items) == 2


def test_ledger_repository_append_only_enforcement(db_session: Session):
    repo = LedgerRepository(db_session)
    entry = LedgerEntry(
        customer_id=1,
        invoice_id=1,
        entry_type=LedgerEntryType.INVOICE_CREATED,
        amount=Decimal("100.00"),
        currency="USD",
        reference_id="INV-1",
        description="Invoice created",
    )
    created = repo.create(entry)
    assert created.id is not None

    # Mutation test: update must raise BusinessRuleViolationException
    with pytest.raises(BusinessRuleViolationException) as exc_info:
        repo.update(created)
    assert "append-only" in str(exc_info.value).lower()

    # Mutation test: delete must raise BusinessRuleViolationException
    with pytest.raises(BusinessRuleViolationException) as exc_info:
        repo.delete(created)
    assert "append-only" in str(exc_info.value).lower()
