from typing import List
from fastapi import APIRouter, Depends, status
from app.api.deps import get_payment_service
from app.services.payment_service import PaymentService
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentAttemptResponse,
    PaymentResultResponse,
)
from app.schemas.invoice import InvoiceResponse

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "",
    response_model=PaymentResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Payment",
    description="Record a payment attempt against an invoice, reconciles balance, and writes to audit ledger.",
)
def record_payment(
    data: PaymentCreateRequest,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResultResponse:
    attempt, invoice = service.record_payment(
        invoice_id=data.invoice_id,
        amount=data.amount,
        status=data.status,
        provider_reference=data.provider_reference,
        currency=data.currency,
        failure_reason=data.failure_reason,
    )
    return PaymentResultResponse(
        payment_attempt=PaymentAttemptResponse.model_validate(attempt),
        invoice=InvoiceResponse.model_validate(invoice),
    )


@router.get(
    "/invoice/{invoice_id}",
    response_model=List[PaymentAttemptResponse],
    summary="List Payment Attempts",
    description="List all recorded payment attempts (success and failed) for a given invoice.",
)
def list_payments_for_invoice(
    invoice_id: int,
    service: PaymentService = Depends(get_payment_service),
) -> List[PaymentAttemptResponse]:
    attempts = service.list_payment_attempts(invoice_id)
    return [PaymentAttemptResponse.model_validate(a) for a in attempts]
