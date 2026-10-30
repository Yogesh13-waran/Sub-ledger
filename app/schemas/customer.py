from datetime import datetime
from typing import Optional
from pydantic import Field, EmailStr
from app.schemas.common import BaseSchema


class CustomerCreate(BaseSchema):
    """Schema for registering a new customer."""
    name: str = Field(..., min_length=1, max_length=255, description="Full name of customer or company")
    email: str = Field(..., min_length=3, max_length=255, description="Unique email address")


class CustomerUpdate(BaseSchema):
    """Schema for updating an existing customer."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, min_length=3, max_length=255)


class CustomerResponse(BaseSchema):
    """Schema returned to API clients representing customer details."""
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime

