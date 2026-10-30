from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_invoice_service
from app.services.invoice_service import InvoiceService
from app.schemas.invoice import InvoiceGenerateRequest, InvoiceResponse

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post(
    "/generate",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Invoice",
    description="Generate a new invoice for an active subscription with snapshot pricing and audit ledger creation.",
)
def generate_invoice(
    data: InvoiceGenerateRequest,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    invoice = service.generate_invoice(
        subscription_id=data.subscription_id,
        period_start=data.period_start,
        period_end=data.period_end,
        due_date=data.due_date,
    )
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "",
    response_model=List[InvoiceResponse],
    summary="List Invoices",
    description="Retrieve invoices with optional customer, subscription, or status filters.",
)
def list_invoices(
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    subscription_id: Optional[int] = Query(None, description="Filter by subscription ID"),
    status: Optional[str] = Query(None, description="Filter by status: issued, partially_paid, paid, cancelled"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: InvoiceService = Depends(get_invoice_service),
) -> List[InvoiceResponse]:
    invoices = service.list_invoices(
        customer_id=customer_id,
        subscription_id=subscription_id,
        status=status,
        skip=skip,
        limit=limit,
    )
    return [InvoiceResponse.model_validate(inv) for inv in invoices]


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get Invoice",
    description="Fetch invoice details by ID.",
)
def get_invoice(
    invoice_id: int,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    invoice = service.get_invoice(invoice_id)
    return InvoiceResponse.model_validate(invoice)
