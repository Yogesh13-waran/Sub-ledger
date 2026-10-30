from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.payment_attempt import PaymentAttempt
from app.repositories.base import BaseRepository


class PaymentAttemptRepository(BaseRepository[PaymentAttempt]):
    """Data access repository for PaymentAttempt entities."""
    def __init__(self, db: Session):
        super().__init__(db, PaymentAttempt)

    def list_by_invoice(self, invoice_id: int, skip: int = 0, limit: int = 100) -> List[PaymentAttempt]:
        """Fetch payment attempts for a given invoice."""
        stmt = (
            select(PaymentAttempt)
            .where(PaymentAttempt.invoice_id == invoice_id)
            .order_by(PaymentAttempt.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_provider_reference(self, provider_reference: str) -> Optional[PaymentAttempt]:
        """Lookup payment attempt by gateway reference ID (for idempotency checks)."""
        stmt = select(PaymentAttempt).where(PaymentAttempt.provider_reference == provider_reference.strip())
        return self.db.scalars(stmt).first()

