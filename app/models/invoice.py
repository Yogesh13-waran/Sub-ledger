from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.base import TimestampMixin, utc_now


class InvoiceStatus:
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"
    VOID = "void"


class Invoice(Base, TimestampMixin):
    """
    Invoice entity representing a billing record generated from a subscription.
    Business rules:
      - amount_due snapshots the plan price at the time of invoice creation.
      - amount_paid tracks cumulative successful payments.
      - status transitions between issued -> partially_paid -> paid.
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount_due = Column(Numeric(12, 2), nullable=False)
    amount_paid = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(String(50), default=InvoiceStatus.ISSUED, nullable=False, index=True)
    
    period_start = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    payment_attempts = relationship(
        "PaymentAttempt",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="desc(PaymentAttempt.created_at)",
    )
    ledger_entries = relationship(
        "LedgerEntry",
        back_populates="invoice",
        order_by="desc(LedgerEntry.created_at)",
    )

    @property
    def remaining_balance(self) -> Decimal:
        """Returns the unpaid amount on the invoice."""
        due = Decimal(str(self.amount_due or 0))
        paid = Decimal(str(self.amount_paid or 0))
        return due - paid

    @property
    def is_fully_paid(self) -> bool:
        """True if invoice is fully paid."""
        return self.amount_paid >= self.amount_due

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} sub_id={self.subscription_id} due={self.amount_due} paid={self.amount_paid} status='{self.status}'>"

