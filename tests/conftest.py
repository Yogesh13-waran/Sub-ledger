import pytest
from typing import Generator
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.main import app
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.base import utc_now

# In-memory SQLite for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yields an isolated database session per test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provides a TestClient with database session dependency overridden."""
    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_customer(db_session: Session) -> Customer:
    """Creates a sample customer fixture."""
    customer = Customer(name="Acme Corp", email="billing@acme.com")
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def sample_plan(db_session: Session) -> Plan:
    """Creates an active sample plan fixture."""
    plan = Plan(
        name="Pro Monthly",
        description="Professional monthly tier",
        price=Decimal("49.99"),
        currency="USD",
        billing_interval="monthly",
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def sample_inactive_plan(db_session: Session) -> Plan:
    """Creates an inactive plan fixture."""
    plan = Plan(
        name="Legacy Tier",
        description="Discontinued tier",
        price=Decimal("19.99"),
        currency="USD",
        billing_interval="monthly",
        is_active=False,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def sample_subscription(db_session: Session, sample_customer: Customer, sample_plan: Plan) -> Subscription:
    """Creates an active subscription fixture."""
    sub = Subscription(
        customer_id=sample_customer.id,
        plan_id=sample_plan.id,
        status=SubscriptionStatus.ACTIVE,
        start_date=utc_now(),
        current_period_start=utc_now(),
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub

