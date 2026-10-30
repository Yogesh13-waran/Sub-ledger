from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Data access repository for Customer entities."""
    def __init__(self, db: Session):
        super().__init__(db, Customer)

    def get_by_email(self, email: str) -> Optional[Customer]:
        """Fetch customer by case-insensitive email."""
        stmt = select(Customer).where(Customer.email.ilike(email.strip()))
        return self.db.scalars(stmt).first()

