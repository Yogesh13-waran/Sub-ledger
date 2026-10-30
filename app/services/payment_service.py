from decimal import Decimal
from typing import Optional, Tuple, List
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment_attempt import PaymentAttempt, PaymentStatus
from app.models.ledger_entry import LedgerEntryType
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_attempt_repository import PaymentAttemptRepository
from app.services.ledger_service import LedgerService
from app.core.exceptions import (
    EntityNotFoundException,
    InvalidPaymentAmountException,
    InvoiceAlreadyPaidException,
    DuplicateResourceException,
    BusinessRuleViolationException,
)


class PaymentService:
    """
    Business service managing payment processing and invoice status reconciliation.
    Enforces business rules:
      - Successful payment cannot exceed remaining unpaid balance on invoice.
      - Fully paid invoice moves to 'paid'; partial payment moves to 'partially_paid'.
      - Failed payment does not increase amount_paid.
      - Ledger entries recorded for both payment_success and payment_failure.
    """
    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        payment_attempt_repo: PaymentAttemptRepository,
        ledger_service: LedgerService,
    ):
        self.invoice_repo = invoice_repo
        self.payment_attempt_repo = payment_attempt_repo
        self.ledger_service = ledger_service

    def record_payment(
        self,
        invoice_id: int,
        amount: Decimal,
        status: str,
        provider_reference: str,
        currency: str = "USD",
        failure_reason: Optional[str] = None,
    ) -> Tuple[PaymentAttempt, Invoice]:
        """
        Execute core payment recording flow:
        1. Fetch and validate target invoice.
        2. Validate payment amount against remaining balance.
        3. Persist payment attempt.
        4. Update invoice amount_paid & status only on success.
        5. Record ledger audit entry.
        """
        # 1. Fetch invoice
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise EntityNotFoundException("Invoice", invoice_id)

        # 2. Validate amount is positive
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
        if amount <= Decimal("0.00"):
            raise BusinessRuleViolationException("Payment amount must be strictly greater than 0.")

        # Idempotency check: prevent duplicate successful processing of same transaction
        existing_attempt = self.payment_attempt_repo.get_by_provider_reference(provider_reference)
        if existing_attempt and existing_attempt.status == PaymentStatus.SUCCESS:
            raise DuplicateResourceException(
                f"Payment with provider reference '{provider_reference}' was already processed successfully."
            )

        status_lower = status.strip().lower()

        # 3. Validate business rules for successful payments
        if status_lower == PaymentStatus.SUCCESS:
            if invoice.is_fully_paid or invoice.status == InvoiceStatus.PAID:
                raise InvoiceAlreadyPaidException(invoice.id)

            remaining = invoice.remaining_balance
            if amount > remaining:
                raise InvalidPaymentAmountException(
                    f"Payment amount of {amount} exceeds remaining unpaid balance of {remaining} on invoice {invoice.id}.",
                    invoice_id=invoice.id,
                    remaining_balance=remaining,
                    attempted_amount=amount,
                )

        # 4. Create payment attempt record
        payment_attempt = PaymentAttempt(
            invoice_id=invoice.id,
            amount=amount,
            currency=currency.upper(),
            status=status_lower,
            provider_reference=provider_reference.strip(),
            failure_reason=failure_reason.strip() if failure_reason else None,
        )
        persisted_attempt = self.payment_attempt_repo.create(payment_attempt)

        # 5. Handle failure branch
        if status_lower == PaymentStatus.FAILED:
            # Rule: failed payment should NOT increase amount_paid
            self.ledger_service.record_entry(
                customer_id=invoice.customer_id,
                invoice_id=invoice.id,
                entry_type=LedgerEntryType.PAYMENT_FAILURE,
                amount=amount,
                currency=currency.upper(),
                reference_id=provider_reference.strip(),
                description=(
                    f"Payment #{persisted_attempt.id} failed for invoice #{invoice.id}. "
                    f"Reason: {failure_reason or 'Payment gateway rejection'}"
                ),
            )
            return persisted_attempt, invoice

        # 6. Handle success branch
        invoice.amount_paid = Decimal(str(invoice.amount_paid)) + amount
        
        # Rule: status transitions to paid or partially_paid
        if invoice.amount_paid >= invoice.amount_due:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        updated_invoice = self.invoice_repo.update(invoice)

        # Rule: record payment_success ledger entry
        self.ledger_service.record_entry(
            customer_id=updated_invoice.customer_id,
            invoice_id=updated_invoice.id,
            entry_type=LedgerEntryType.PAYMENT_SUCCESS,
            amount=amount,
            currency=currency.upper(),
            reference_id=provider_reference.strip(),
            description=(
                f"Payment #{persisted_attempt.id} succeeded. Applied {currency} {amount} "
                f"to invoice #{updated_invoice.id}. New status: {updated_invoice.status}."
            ),
        )

        return persisted_attempt, updated_invoice

    def list_payment_attempts(self, invoice_id: int) -> List[PaymentAttempt]:
        """Fetch all payment attempts recorded for an invoice."""
        return self.payment_attempt_repo.list_by_invoice(invoice_id)
