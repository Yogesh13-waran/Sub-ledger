from typing import List, Optional
from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.core.exceptions import EntityNotFoundException, DuplicateResourceException


class CustomerService:
    """
    Business service for managing Customer lifecycle.
    Enforces business rule: Customer email must be unique.
    """
    def __init__(self, customer_repo: CustomerRepository):
        self.customer_repo = customer_repo

    def create_customer(self, data: CustomerCreate) -> Customer:
        """Register a new customer with unique email validation."""
        existing = self.customer_repo.get_by_email(data.email)
        if existing:
            raise DuplicateResourceException(
                f"Customer with email '{data.email}' already exists.",
                resource="Customer",
            )
        customer = Customer(
            name=data.name.strip(),
            email=data.email.strip().lower(),
        )
        return self.customer_repo.create(customer)

    def get_customer(self, customer_id: int) -> Customer:
        """Fetch customer by ID or raise EntityNotFoundException."""
        customer = self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise EntityNotFoundException("Customer", customer_id)
        return customer

    def list_customers(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        """List customers with pagination."""
        return self.customer_repo.list(skip=skip, limit=limit)

    def count_customers(self) -> int:
        """Count total customers."""
        return self.customer_repo.count()

    def update_customer(self, customer_id: int, data: CustomerUpdate) -> Customer:
        """Update customer fields with unique email validation."""
        customer = self.get_customer(customer_id)
        if data.email is not None and data.email.strip().lower() != customer.email.lower():
            existing = self.customer_repo.get_by_email(data.email)
            if existing and existing.id != customer.id:
                raise DuplicateResourceException(
                    f"Customer with email '{data.email}' already exists.",
                    resource="Customer",
                )
            customer.email = data.email.strip().lower()

        if data.name is not None:
            customer.name = data.name.strip()

        return self.customer_repo.update(customer)
