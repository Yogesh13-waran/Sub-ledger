from typing import Optional, Any, Dict


class SubLedgerException(Exception):
    """Base exception for all domain-specific errors in SubLedger."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundException(SubLedgerException):
    """Raised when an entity is not found in the repository."""
    def __init__(self, entity_name: str, entity_id: Any):
        message = f"{entity_name} with identifier '{entity_id}' was not found."
        super().__init__(message, {"entity_name": entity_name, "entity_id": str(entity_id)})


class DuplicateResourceException(SubLedgerException):
    """Raised when a unique constraint or idempotency conflict occurs."""
    def __init__(self, message: str, resource: Optional[str] = None):
        super().__init__(message, {"resource": resource} if resource else {})


class BusinessRuleViolationException(SubLedgerException):
    """Base exception for domain business rule violations."""
    pass


class InactivePlanException(BusinessRuleViolationException):
    """Raised when an operation targets an inactive plan."""
    def __init__(self, plan_id: int):
        super().__init__(
            f"Cannot create subscription: Plan id {plan_id} is inactive.",
            {"plan_id": plan_id}
        )


class DuplicateActiveSubscriptionException(BusinessRuleViolationException):
    """Raised when a customer already has an active subscription to the same plan."""
    def __init__(self, customer_id: int, plan_id: int):
        super().__init__(
            f"Customer {customer_id} already has an active subscription to Plan {plan_id}.",
            {"customer_id": customer_id, "plan_id": plan_id}
        )


class InvalidPaymentAmountException(BusinessRuleViolationException):
    """Raised when payment exceeds the invoice unpaid balance or is non-positive."""
    def __init__(self, message: str, invoice_id: int, remaining_balance: Any, attempted_amount: Any):
        super().__init__(
            message,
            {
                "invoice_id": invoice_id,
                "remaining_balance": str(remaining_balance),
                "attempted_amount": str(attempted_amount),
            }
        )


class InvoiceAlreadyPaidException(BusinessRuleViolationException):
    """Raised when attempting to pay an invoice that is already fully paid."""
    def __init__(self, invoice_id: int):
        super().__init__(
            f"Invoice {invoice_id} is already fully paid. No further payments can be accepted.",
            {"invoice_id": invoice_id}
        )
