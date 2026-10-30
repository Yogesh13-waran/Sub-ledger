from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseSchema


class InvoiceGenerateRequest(BaseSchema):
    """Schema for requesting manual or automated invoice generation for a subscription."""
    subscription_id: int = Field(..., description="ID of active subscription")
    period_start: Optional[datetime] = Field(None, description="Optional override for billing cycle start")
    period_end: Optional[datetime] = Field(None, description="Optional override for billing cycle end")
    due_date: Optional[datetime] = Field(None, description="Optional invoice due date")


class InvoiceResponse(BaseSchema):
    """Schema representing an invoice."""
    id: int
    subscription_id: int
    customer_id: int
    amount_due: Decimal
    amount_paid: Decimal
    remaining_balance: Decimal
    currency: str
    status: str
    period_start: datetime
    period_end: datetime
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
