from datetime import timedelta
from typing import List, Optional
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.base import utc_now
from app.repositories.customer_repository import CustomerRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.subscription import SubscriptionCreate
from app.core.exceptions import (
    EntityNotFoundException,
    InactivePlanException,
    DuplicateActiveSubscriptionException,
    BusinessRuleViolationException,
)


class SubscriptionService:
    """
    Business service for managing subscriptions.
    Enforces business rules:
      - A subscription cannot be created for an inactive plan.
      - A customer cannot have two active subscriptions to the same plan in the base version.
    """
    def __init__(
        self,
        customer_repo: CustomerRepository,
        plan_repo: PlanRepository,
        subscription_repo: SubscriptionRepository,
    ):
        self.customer_repo = customer_repo
        self.plan_repo = plan_repo
        self.subscription_repo = subscription_repo

    def create_subscription(self, data: SubscriptionCreate) -> Subscription:
        """
        Create a subscription after validating customer existence, plan availability,
        and single-active-subscription per plan constraint.
        """
        # 1. Validate customer exists
        customer = self.customer_repo.get_by_id(data.customer_id)
        if not customer:
            raise EntityNotFoundException("Customer", data.customer_id)

        # 2. Validate plan exists
        plan = self.plan_repo.get_by_id(data.plan_id)
        if not plan:
            raise EntityNotFoundException("Plan", data.plan_id)

        # 3. Business rule: Cannot create subscription for inactive plan
        if not plan.is_active:
            raise InactivePlanException(plan.id)

        # 4. Business rule: No duplicate active subscription for the same plan
        existing_active = self.subscription_repo.get_active_by_customer_and_plan(
            customer_id=data.customer_id,
            plan_id=data.plan_id,
        )
        if existing_active:
            raise DuplicateActiveSubscriptionException(data.customer_id, data.plan_id)

        now = utc_now()
        # Compute default period end based on billing frequency
        interval_days = 365 if plan.billing_interval == "yearly" else 30
        period_end = now + timedelta(days=interval_days)

        subscription = Subscription(
            customer_id=data.customer_id,
            plan_id=data.plan_id,
            status=SubscriptionStatus.ACTIVE,
            start_date=now,
            current_period_start=now,
            current_period_end=period_end,
        )
        return self.subscription_repo.create(subscription)

    def get_subscription(self, subscription_id: int) -> Subscription:
        """Fetch subscription by ID or raise EntityNotFoundException."""
        sub = self.subscription_repo.get_by_id(subscription_id)
        if not sub:
            raise EntityNotFoundException("Subscription", subscription_id)
        return sub

    def list_subscriptions(
        self,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Subscription]:
        """List subscriptions with optional customer/status filters."""
        if customer_id is not None:
            return self.subscription_repo.list_by_customer(customer_id, skip=skip, limit=limit)
        if status is not None:
            return self.subscription_repo.list_by_status(status, skip=skip, limit=limit)
        return self.subscription_repo.list(skip=skip, limit=limit)

    def cancel_subscription(self, subscription_id: int) -> Subscription:
        """Cancel an active subscription."""
        subscription = self.get_subscription(subscription_id)
        if subscription.status == SubscriptionStatus.CANCELLED:
            raise BusinessRuleViolationException(
                f"Subscription {subscription_id} is already cancelled."
            )

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = utc_now()
        return self.subscription_repo.update(subscription)

