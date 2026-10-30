import pytest
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.invoice import InvoiceStatus
from app.models.payment_attempt import PaymentStatus
from app.models.ledger_entry import LedgerEntryType

from app.repositories.customer_repository import CustomerRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_attempt_repository import PaymentAttemptRepository
from app.repositories.ledger_repository import LedgerRepository

from app.services.customer_service import CustomerService
from app.services.plan_service import PlanService
from app.services.subscription_service import SubscriptionService
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService
from app.services.ledger_service import LedgerService

from app.schemas.customer import CustomerCreate
from app.schemas.plan import PlanCreate
from app.schemas.subscription import SubscriptionCreate

from app.core.exceptions import (
    BusinessRuleViolationException,
    DuplicateResourceException,
    InactivePlanException,
    DuplicateActiveSubscriptionException,
    InvalidPaymentAmountException,
    InvoiceAlreadyPaidException,
)


# --- Fixtures for Services ---

@pytest.fixture
def customer_service(db_session: Session) -> CustomerService:
    return CustomerService(CustomerRepository(db_session))


@pytest.fixture
def plan_service(db_session: Session) -> PlanService:
    return PlanService(PlanRepository(db_session))


@pytest.fixture
def ledger_service(db_session: Session) -> LedgerService:
    return LedgerService(LedgerRepository(db_session))


@pytest.fixture
def subscription_service(db_session: Session) -> SubscriptionService:
    return SubscriptionService(
        customer_repo=CustomerRepository(db_session),
        plan_repo=PlanRepository(db_session),
        subscription_repo=SubscriptionRepository(db_session),
    )


@pytest.fixture
def invoice_service(db_session: Session, ledger_service: LedgerService) -> InvoiceService:
    return InvoiceService(
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=PlanRepository(db_session),
        invoice_repo=InvoiceRepository(db_session),
        ledger_service=ledger_service,
    )


@pytest.fixture
def payment_service(db_session: Session, ledger_service: LedgerService) -> PaymentService:
    return PaymentService(
        invoice_repo=InvoiceRepository(db_session),
        payment_attempt_repo=PaymentAttemptRepository(db_session),
        ledger_service=ledger_service,
    )


# --- 1. Plan Price Validation ---

def test_plan_price_must_be_greater_than_zero(plan_service: PlanService):
    """Business Rule 1: Plan price must be strictly greater than 0."""
    with pytest.raises(Exception):
        plan_service.create_plan(
            PlanCreate(name="Free Tier", price=Decimal("0.00"), billing_interval="monthly")
        )

    with pytest.raises(Exception):
        plan_service.create_plan(
            PlanCreate(name="Negative Tier", price=Decimal("-10.00"), billing_interval="monthly")
        )

    # Valid plan
    valid_plan = plan_service.create_plan(
        PlanCreate(name="Valid Plan", price=Decimal("29.99"), billing_interval="monthly")
    )
    assert valid_plan.id is not None
    assert valid_plan.price == Decimal("29.99")


# --- 2. Customer Email Uniqueness ---

def test_customer_email_must_be_unique(customer_service: CustomerService):
    """Business Rule 2: Customer email must be unique."""
    customer_service.create_customer(CustomerCreate(name="Alpha Corp", email="contact@alpha.com"))

    with pytest.raises(DuplicateResourceException) as exc_info:
        customer_service.create_customer(CustomerCreate(name="Alpha Second", email="CONTACT@alpha.com"))
    assert "already exists" in str(exc_info.value).lower()


# --- 3. Inactive Plan Subscription Prevention ---

def test_cannot_subscribe_to_inactive_plan(
    subscription_service: SubscriptionService,
    sample_customer: Customer,
    sample_inactive_plan: Plan,
):
    """Business Rule 3: A subscription cannot be created for an inactive plan."""
    with pytest.raises(InactivePlanException) as exc_info:
        subscription_service.create_subscription(
            SubscriptionCreate(customer_id=sample_customer.id, plan_id=sample_inactive_plan.id)
        )
    assert "inactive" in str(exc_info.value).lower()


# --- 4. Duplicate Active Subscription Prevention ---

def test_cannot_have_two_active_subscriptions_to_same_plan(
    subscription_service: SubscriptionService,
    sample_customer: Customer,
    sample_plan: Plan,
):
    """Business Rule 4: A customer cannot have two active subscriptions to the same plan."""
    # First subscription succeeds
    sub1 = subscription_service.create_subscription(
        SubscriptionCreate(customer_id=sample_customer.id, plan_id=sample_plan.id)
    )
    assert sub1.id is not None

    # Second active subscription to same plan must fail
    with pytest.raises(DuplicateActiveSubscriptionException) as exc_info:
        subscription_service.create_subscription(
            SubscriptionCreate(customer_id=sample_customer.id, plan_id=sample_plan.id)
        )
    assert "already has an active subscription" in str(exc_info.value).lower()


# --- 5. Invoice Snapshot Pricing & Ledger Entry ---

def test_invoice_generation_snapshot_pricing_and_ledger(
    invoice_service: InvoiceService,
    ledger_service: LedgerService,
    plan_service: PlanService,
    sample_subscription: Subscription,
    sample_plan: Plan,
):
    """
    Business Rule 5: Invoice amount_due comes from plan price at the time invoice is generated.
    Business Rule 9: Ledger entry invoice_created is created with reference_id.
    """
    invoice = invoice_service.generate_invoice(subscription_id=sample_subscription.id)
    assert invoice.id is not None
    assert invoice.amount_due == sample_plan.price
    assert invoice.amount_paid == Decimal("0.00")
    assert invoice.status == InvoiceStatus.ISSUED

    # Verify snapshot behavior: if plan price changes subsequently, existing invoice stays identical!
    plan_service.update_plan(sample_plan.id, PlanCreate(name=sample_plan.name, price=Decimal("99.99")))
    fetched_inv = invoice_service.get_invoice(invoice.id)
    assert fetched_inv.amount_due == Decimal("49.99")  # Remains 49.99 snapshot!

    # Verify ledger audit entry
    entries = ledger_service.get_by_reference_id(f"INV-{invoice.id}")
    assert len(entries) == 1
    assert entries[0].entry_type == LedgerEntryType.INVOICE_CREATED
    assert entries[0].amount == Decimal("49.99")
    assert entries[0].customer_id == sample_subscription.customer_id


# --- 6, 7, 8. Payment Recording, Status Progression, and Failure Isolation ---

def test_payment_recording_flow_and_business_rules(
    invoice_service: InvoiceService,
    payment_service: PaymentService,
    ledger_service: LedgerService,
    sample_subscription: Subscription,
):
    """
    Tests:
    - Business Rule 6: Successful payment cannot exceed remaining unpaid balance.
    - Business Rule 7: Partial payment moves to partially_paid; full payment moves to paid.
    - Business Rule 8: Failed payment does not increase amount_paid.
    - Business Rule 9: Ledger entries recorded for payment_success and payment_failure.
    """
    invoice = invoice_service.generate_invoice(subscription_id=sample_subscription.id)
    total_due = invoice.amount_due  # 49.99

    # 1. Test failed payment: amount_paid must not change!
    failed_attempt, inv_after_fail = payment_service.record_payment(
        invoice_id=invoice.id,
        amount=Decimal("15.00"),
        status=PaymentStatus.FAILED,
        provider_reference="TX_FAIL_001",
        failure_reason="Insufficient balance",
    )
    assert failed_attempt.status == PaymentStatus.FAILED
    assert inv_after_fail.amount_paid == Decimal("0.00")
    assert inv_after_fail.status == InvoiceStatus.ISSUED

    # Verify payment_failure ledger entry
    fail_ledger = ledger_service.get_by_reference_id("TX_FAIL_001")
    assert len(fail_ledger) == 1
    assert fail_ledger[0].entry_type == LedgerEntryType.PAYMENT_FAILURE

    # 2. Test overpayment rejection: cannot exceed remaining amount!
    with pytest.raises(InvalidPaymentAmountException) as exc_info:
        payment_service.record_payment(
            invoice_id=invoice.id,
            amount=Decimal("60.00"),  # Exceeds 49.99
            status=PaymentStatus.SUCCESS,
            provider_reference="TX_OVERPAY",
        )
    assert "exceeds remaining unpaid balance" in str(exc_info.value).lower()

    # 3. Test partial payment (20.00 out of 49.99)
    part_attempt, inv_after_part = payment_service.record_payment(
        invoice_id=invoice.id,
        amount=Decimal("20.00"),
        status=PaymentStatus.SUCCESS,
        provider_reference="TX_PART_001",
    )
    assert part_attempt.status == PaymentStatus.SUCCESS
    assert inv_after_part.amount_paid == Decimal("20.00")
    assert inv_after_part.remaining_balance == Decimal("29.99")
    assert inv_after_part.status == InvoiceStatus.PARTIALLY_PAID

    # 4. Test final payment (remaining 29.99)
    final_attempt, inv_after_full = payment_service.record_payment(
        invoice_id=invoice.id,
        amount=Decimal("29.99"),
        status=PaymentStatus.SUCCESS,
        provider_reference="TX_FULL_002",
    )
    assert final_attempt.status == PaymentStatus.SUCCESS
    assert inv_after_full.amount_paid == Decimal("49.99")
    assert inv_after_full.remaining_balance == Decimal("0.00")
    assert inv_after_full.status == InvoiceStatus.PAID

    # 5. Test payment on fully paid invoice
    with pytest.raises(InvoiceAlreadyPaidException):
        payment_service.record_payment(
            invoice_id=invoice.id,
            amount=Decimal("5.00"),
            status=PaymentStatus.SUCCESS,
            provider_reference="TX_EXTRA",
        )

