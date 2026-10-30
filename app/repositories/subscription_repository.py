from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.subscription import Subscription, SubscriptionStatus
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    """Data access repository for Subscription entities."""
    def __init__(self, db: Session):
        super().__init__(db, Subscription)

    def get_active_by_customer_and_plan(self, customer_id: int, plan_id: int) -> Optional[Subscription]:
        """
        Check if customer already has an active subscription to a specific plan.
        Enforces Business Rule: Customer cannot have two active subscriptions to the same plan.
        """
        stmt = (
            select(Subscription)
            .where(
                Subscription.customer_id == customer_id,
                Subscription.plan_id == plan_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        return self.db.scalars(stmt).first()

    def list_by_customer(self, customer_id: int, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """Fetch all subscriptions for a specific customer."""
        stmt = (
            select(Subscription)
            .where(Subscription.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """Fetch subscriptions by status."""
        stmt = (
            select(Subscription)
            .where(Subscription.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
