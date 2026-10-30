from datetime import datetime
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseSchema


class SubscriptionCreate(BaseSchema):
    """Schema for subscribing a customer to a plan."""
    customer_id: int = Field(..., description="Target customer identifier")
    plan_id: int = Field(..., description="Target plan identifier")


class SubscriptionResponse(BaseSchema):
    """Schema representing subscription state."""
    id: int
    customer_id: int
    plan_id: int
    status: str
    start_date: datetime
    current_period_start: datetime
    current_period_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
