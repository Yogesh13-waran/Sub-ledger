from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.base import TimestampMixin, utc_now


class SubscriptionStatus:
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    EXPIRED = "expired"


class Subscription(Base, TimestampMixin):
    """
    Subscription entity linking a Customer to a Plan.
    Business rules: Cannot be created on an inactive plan;
    Customer cannot have two active subscriptions to the same plan.
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    status = Column(String(50), default=SubscriptionStatus.ACTIVE, nullable=False, index=True)
    
    start_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    current_period_start = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    invoices = relationship(
        "Invoice",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="desc(Invoice.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} customer_id={self.customer_id} plan_id={self.plan_id} status='{self.status}'>"

