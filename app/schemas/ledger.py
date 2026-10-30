from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.schemas.common import BaseSchema


class LedgerEntryResponse(BaseSchema):
    """Schema representing an append-only ledger entry for audit trail."""
    id: int
    customer_id: Optional[int] = None
    invoice_id: Optional[int] = None
    entry_type: str
    amount: Decimal
    currency: str
    reference_id: str
    description: str
    created_at: datetime

