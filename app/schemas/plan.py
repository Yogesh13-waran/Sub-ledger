from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field, field_validator
from app.schemas.common import BaseSchema


class PlanCreate(BaseSchema):
    """Schema for creating a new pricing plan."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    price: Decimal = Field(..., description="Plan recurring price, must be strictly > 0")
    currency: str = Field("USD", min_length=3, max_length=3)
    billing_interval: str = Field("monthly", description="Billing frequency: monthly, yearly")
    is_active: bool = Field(True, description="Whether plan is available for new subscriptions")

    @field_validator("price")
    @classmethod
    def validate_price_greater_than_zero(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0.00"):
            raise ValueError("Plan price must be strictly greater than 0.")
        return v.quantize(Decimal("0.01"))


class PlanUpdate(BaseSchema):
    """Schema for updating an existing plan."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[Decimal] = Field(None, description="Must be > 0 if provided")
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    billing_interval: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("price")
    @classmethod
    def validate_price_if_provided(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= Decimal("0.00"):
            raise ValueError("Plan price must be strictly greater than 0.")
        return v.quantize(Decimal("0.01")) if v is not None else None


class PlanResponse(BaseSchema):
    """Schema returned to API clients representing a plan."""
    id: int
    name: str
    description: Optional[str]
    price: Decimal
    currency: str
    billing_interval: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
