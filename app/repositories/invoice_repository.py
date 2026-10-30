from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.invoice import Invoice
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Data access repository for Invoice entities."""
    def __init__(self, db: Session):
        super().__init__(db, Invoice)

    def list_by_customer(self, customer_id: int, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Fetch invoices belonging to a specific customer."""
        stmt = (
            select(Invoice)
            .where(Invoice.customer_id == customer_id)
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_by_subscription(self, subscription_id: int, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Fetch invoices belonging to a specific subscription."""
        stmt = (
            select(Invoice)
            .where(Invoice.subscription_id == subscription_id)
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Fetch invoices by payment status."""
        stmt = (
            select(Invoice)
            .where(Invoice.status == status)
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
