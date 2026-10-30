from decimal import Decimal
from typing import List, Optional
from app.models.plan import Plan
from app.repositories.plan_repository import PlanRepository
from app.schemas.plan import PlanCreate, PlanUpdate
from app.core.exceptions import EntityNotFoundException, BusinessRuleViolationException


class PlanService:
    """
    Business service for Plan management.
    Enforces business rule: Plan price must be strictly greater than 0.
    """
    def __init__(self, plan_repo: PlanRepository):
        self.plan_repo = plan_repo

    def create_plan(self, data: PlanCreate) -> Plan:
        """Create a new pricing plan ensuring price > 0."""
        if data.price <= Decimal("0.00"):
            raise BusinessRuleViolationException("Plan price must be strictly greater than 0.")
        
        plan = Plan(
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            price=data.price,
            currency=data.currency.upper(),
            billing_interval=data.billing_interval.lower(),
            is_active=data.is_active,
        )
        return self.plan_repo.create(plan)

    def get_plan(self, plan_id: int) -> Plan:
        """Fetch plan by ID or raise EntityNotFoundException."""
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise EntityNotFoundException("Plan", plan_id)
        return plan

    def list_plans(self, active_only: bool = False, skip: int = 0, limit: int = 100) -> List[Plan]:
        """List plans with optional active filter and pagination."""
        if active_only:
            return self.plan_repo.list_active(skip=skip, limit=limit)
        return self.plan_repo.list(skip=skip, limit=limit)

    def count_plans(self) -> int:
        """Count total plans."""
        return self.plan_repo.count()

    def update_plan(self, plan_id: int, data: PlanUpdate) -> Plan:
        """Update existing plan attributes."""
        plan = self.get_plan(plan_id)
        if data.price is not None:
            if data.price <= Decimal("0.00"):
                raise BusinessRuleViolationException("Plan price must be strictly greater than 0.")
            plan.price = data.price
        if data.name is not None:
            plan.name = data.name.strip()
        if data.description is not None:
            plan.description = data.description.strip()
        if data.currency is not None:
            plan.currency = data.currency.upper()
        if data.billing_interval is not None:
            plan.billing_interval = data.billing_interval.lower()
        if data.is_active is not None:
            plan.is_active = data.is_active

        return self.plan_repo.update(plan)

