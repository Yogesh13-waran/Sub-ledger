from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.base import TimestampMixin


class Customer(Base, TimestampMixin):
    """
    Customer entity representing a subscriber/client in SubLedger.
    Business rules: Email must be unique.
    """
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)

    # Relationships
    subscriptions = relationship(
        "Subscription",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="desc(Subscription.created_at)",
    )
    invoices = relationship(
        "Invoice",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="desc(Invoice.created_at)",
    )
    ledger_entries = relationship(
        "LedgerEntry",
        back_populates="customer",
        order_by="desc(LedgerEntry.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email='{self.email}'>"
