from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field, field_validator
from app.schemas.common import BaseSchema
from app.schemas.invoice import InvoiceResponse


class PaymentCreateRequest(BaseSchema):
    """Schema for recording a payment attempt against an invoice."""
    invoice_id: int = Field(..., description="ID of invoice to apply payment toward")
    amount: Decimal = Field(..., description="Payment amount, must be strictly > 0")
    currency: str = Field("USD", min_length=3, max_length=3)
    status: str = Field("success", description="Payment attempt result: 'success' or 'failed'")
    provider_reference: str = Field(..., min_length=1, max_length=255, description="Gateway transaction reference")
    failure_reason: Optional[str] = Field(None, max_length=500, description="Error reason if status is failed")

    @field_validator("amount")
    @classmethod
    def validate_amount_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0.00"):
            raise ValueError("Payment amount must be strictly greater than 0.")
        return v.quantize(Decimal("0.01"))

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ("success", "failed"):
            raise ValueError("Payment status must be either 'success' or 'failed'.")
        return cleaned


class PaymentAttemptResponse(BaseSchema):
    """Schema representing recorded payment attempt details."""
    id: int
    invoice_id: int
    amount: Decimal
    currency: str
    status: str
    provider_reference: str
    failure_reason: Optional[str] = None
    created_at: datetime


class PaymentResultResponse(BaseSchema):
    """Schema returned by payment service containing attempt and updated invoice status."""
    payment_attempt: PaymentAttemptResponse
    invoice: InvoiceResponse

