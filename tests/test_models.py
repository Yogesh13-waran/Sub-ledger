from decimal import Decimal
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment_attempt import PaymentAttempt, PaymentStatus
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.models.base import utc_now


def test_customer_model_repr():
    c = Customer(id=1, name="Jane", email="jane@test.com")
    assert repr(c) == "<Customer id=1 email='jane@test.com'>"


def test_plan_model_repr():
    p = Plan(id=5, name="Pro", price=Decimal("29.99"), is_active=True)
    assert repr(p) == "<Plan id=5 name='Pro' price=29.99 active=True>"


def test_subscription_model_repr():
    s = Subscription(id=10, customer_id=1, plan_id=5, status=SubscriptionStatus.ACTIVE)
    assert repr(s) == "<Subscription id=10 customer_id=1 plan_id=5 status='active'>"


def test_invoice_properties():
    inv = Invoice(
        id=100,
        subscription_id=10,
        customer_id=1,
        amount_due=Decimal("150.00"),
        amount_paid=Decimal("50.00"),
        currency="USD",
        status=InvoiceStatus.ISSUED,
        period_start=utc_now(),
        period_end=utc_now(),
    )
    assert inv.remaining_balance == Decimal("100.00")
    assert not inv.is_fully_paid
    assert repr(inv) == "<Invoice id=100 sub_id=10 due=150.00 paid=50.00 status='issued'>"

    # Fully paid check
    inv.amount_paid = Decimal("150.00")
    assert inv.remaining_balance == Decimal("0.00")
    assert inv.is_fully_paid


def test_payment_attempt_and_ledger_repr():
    attempt = PaymentAttempt(
        id=77,
        invoice_id=100,
        amount=Decimal("50.00"),
        currency="USD",
        status=PaymentStatus.SUCCESS,
        provider_reference="ref_123",
    )
    assert repr(attempt) == "<PaymentAttempt id=77 invoice_id=100 amount=50.00 status='success'>"

    ledger = LedgerEntry(
        id=99,
        entry_type=LedgerEntryType.PAYMENT_SUCCESS,
        amount=Decimal("50.00"),
        currency="USD",
        reference_id="ref_123",
        description="Payment test",
    )
    assert repr(ledger) == "<LedgerEntry id=99 type='payment_success' amount=50.00 ref='ref_123'>"

