from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.base import utc_now


class PaymentStatus:
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class PaymentAttempt(Base):
    """
    PaymentAttempt entity representing a transaction against an invoice.
    Business rules:
      - Successful payment cannot exceed remaining invoice balance.
      - Failed payment stores failure_reason and leaves amount_paid unchanged.
    """
    __tablename__ = "payment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(String(50), nullable=False, index=True)
    provider_reference = Column(String(255), nullable=False, index=True)
    failure_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="payment_attempts")

    def __repr__(self) -> str:
        return f"<PaymentAttempt id={self.id} invoice_id={self.invoice_id} amount={self.amount} status='{self.status}'>"
