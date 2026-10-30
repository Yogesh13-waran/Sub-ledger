from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standardized response envelope for API endpoints."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated list response envelope."""
    total: int
    items: List[T]
    page: int = 1
    page_size: int = 50


class BaseSchema(BaseModel):
    """Base Pydantic model with from_attributes configured for SQLAlchemy ORM conversion."""
    model_config = ConfigDict(from_attributes=True)
