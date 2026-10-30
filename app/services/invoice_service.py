from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List
from app.models.invoice import Invoice, InvoiceStatus
from app.models.subscription import SubscriptionStatus
from app.models.ledger_entry import LedgerEntryType
from app.models.base import utc_now
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.services.ledger_service import LedgerService
from app.core.exceptions import (
    EntityNotFoundException,
    BusinessRuleViolationException,
)


class InvoiceService:
    """
    Business service managing invoice generation and retrieval.
    Enforces business rules:
      - Subscription must exist and be active to generate an invoice.
      - Invoice amount_due snapshots plan price at time of generation.
      - Generates an immutable invoice_created ledger entry.
    """
    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        plan_repo: PlanRepository,
        invoice_repo: InvoiceRepository,
        ledger_service: LedgerService,
    ):
        self.subscription_repo = subscription_repo
        self.plan_repo = plan_repo
        self.invoice_repo = invoice_repo
        self.ledger_service = ledger_service

    def generate_invoice(
        self,
        subscription_id: int,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
    ) -> Invoice:
        """
        Execute core invoice generation flow:
        1. Fetch and validate active subscription.
        2. Snapshot plan price into amount_due.
        3. Compute billing period & due date.
        4. Persist invoice in database.
        5. Record invoice_created ledger entry.
        """
        # 1. Fetch subscription
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise EntityNotFoundException("Subscription", subscription_id)

        # 2. Verify subscription is active
        if subscription.status != SubscriptionStatus.ACTIVE:
            raise BusinessRuleViolationException(
                f"Cannot generate invoice: Subscription {subscription_id} is {subscription.status}."
            )

        # 3. Snapshot plan details
        plan = self.plan_repo.get_by_id(subscription.plan_id)
        if not plan:
            raise EntityNotFoundException("Plan", subscription.plan_id)

        now = utc_now()
        resolved_start = period_start or subscription.current_period_start or now
        default_interval = 365 if plan.billing_interval == "yearly" else 30
        resolved_end = period_end or subscription.current_period_end or (resolved_start + timedelta(days=default_interval))
        resolved_due_date = due_date or (now + timedelta(days=14))

        # 4. Create invoice with plan price snapshot
        invoice = Invoice(
            subscription_id=subscription.id,
            customer_id=subscription.customer_id,
            amount_due=plan.price,
            amount_paid=Decimal("0.00"),
            currency=plan.currency,
            status=InvoiceStatus.ISSUED,
            period_start=resolved_start,
            period_end=resolved_end,
            due_date=resolved_due_date,
        )
        persisted_invoice = self.invoice_repo.create(invoice)

        # 5. Create invoice_created ledger entry
        self.ledger_service.record_entry(
            customer_id=persisted_invoice.customer_id,
            invoice_id=persisted_invoice.id,
            entry_type=LedgerEntryType.INVOICE_CREATED,
            amount=persisted_invoice.amount_due,
            currency=persisted_invoice.currency,
            reference_id=f"INV-{persisted_invoice.id}",
            description=(
                f"Invoice #{persisted_invoice.id} created for subscription "
                f"#{subscription.id} - Plan '{plan.name}' ({plan.currency} {plan.price})"
            ),
        )

        return persisted_invoice

    def get_invoice(self, invoice_id: int) -> Invoice:
        """Fetch invoice by ID or raise EntityNotFoundException."""
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise EntityNotFoundException("Invoice", invoice_id)
        return invoice

    def list_invoices(
        self,
        customer_id: Optional[int] = None,
        subscription_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Invoice]:
        """List invoices with optional filters."""
        if customer_id is not None:
            return self.invoice_repo.list_by_customer(customer_id, skip=skip, limit=limit)
        if subscription_id is not None:
            return self.invoice_repo.list_by_subscription(subscription_id, skip=skip, limit=limit)
        if status is not None:
            return self.invoice_repo.list_by_status(status, skip=skip, limit=limit)
        return self.invoice_repo.list(skip=skip, limit=limit)

