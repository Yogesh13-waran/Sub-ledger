from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.plan import Plan
from app.repositories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    """Data access repository for Plan entities."""
    def __init__(self, db: Session):
        super().__init__(db, Plan)

    def list_active(self, skip: int = 0, limit: int = 100) -> List[Plan]:
        """Fetch all active plans."""
        stmt = (
            select(Plan)
            .where(Plan.is_active == True) # noqa: E712
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

