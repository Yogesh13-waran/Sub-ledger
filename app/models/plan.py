from sqlalchemy import Column, Integer, String, Numeric, Boolean
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.base import TimestampMixin


class Plan(Base, TimestampMixin):
    """
    Plan entity representing a pricing tier / subscription plan.
    Business rules: Price must be greater than 0; is_active controls availability.
    """
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    billing_interval = Column(String(50), default="monthly", nullable=False)  # monthly, yearly
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    subscriptions = relationship(
        "Subscription",
        back_populates="plan",
        order_by="desc(Subscription.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Plan id={self.id} name='{self.name}' price={self.price} active={self.is_active}>"
