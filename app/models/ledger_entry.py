from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.base import utc_now


class LedgerEntryType:
    INVOICE_CREATED = "invoice_created"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILURE = "payment_failure"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class LedgerEntry(Base):
    """
    LedgerEntry entity representing an immutable, append-only financial audit event.
    Business rules:
      - Append-only (never updated or deleted).
      - Traceable through reference_id (links back to invoice or payment attempt).
    """
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entry_type = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    reference_id = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="ledger_entries")
    invoice = relationship("Invoice", back_populates="ledger_entries")

    def __repr__(self) -> str:
        return f"<LedgerEntry id={self.id} type='{self.entry_type}' amount={self.amount} ref='{self.reference_id}'>"

