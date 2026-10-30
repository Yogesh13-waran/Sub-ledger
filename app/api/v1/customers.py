from typing import List
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_customer_service
from app.services.customer_service import CustomerService
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Customer",
    description="Create a new customer profile. Validates that email is globally unique.",
)
def create_customer(
    data: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    customer = service.create_customer(data)
    return CustomerResponse.model_validate(customer)


@router.get(
    "",
    response_model=List[CustomerResponse],
    summary="List Customers",
    description="Retrieve paginated list of customers.",
)
def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: CustomerService = Depends(get_customer_service),
) -> List[CustomerResponse]:
    customers = service.list_customers(skip=skip, limit=limit)
    return [CustomerResponse.model_validate(c) for c in customers]


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get Customer",
    description="Fetch a customer profile by its primary identifier.",
)
def get_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    customer = service.get_customer(customer_id)
    return CustomerResponse.model_validate(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update Customer",
    description="Modify customer details with uniqueness validation.",
)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    customer = service.update_customer(customer_id, data)
    return CustomerResponse.model_validate(customer)
