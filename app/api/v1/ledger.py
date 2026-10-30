from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_ledger_service
from app.services.ledger_service import LedgerService
from app.schemas.ledger import LedgerEntryResponse

router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.get(
    "",
    response_model=List[LedgerEntryResponse],
    summary="List Ledger Entries",
    description="Retrieve immutable financial audit ledger entries filtered by customer, invoice, entry_type, or reference ID.",
)
def list_ledger_entries(
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    entry_type: Optional[str] = Query(None, description="Filter by entry type (e.g. invoice_created, payment_success, payment_failure)"),
    reference_id: Optional[str] = Query(None, description="Filter by transaction reference ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: LedgerService = Depends(get_ledger_service),
) -> List[LedgerEntryResponse]:
    entries = service.list_entries(
        customer_id=customer_id,
        invoice_id=invoice_id,
        entry_type=entry_type,
        reference_id=reference_id,
        skip=skip,
        limit=limit,
    )
    return [LedgerEntryResponse.model_validate(e) for e in entries]


@router.get(
    "/{entry_id}",
    response_model=LedgerEntryResponse,
    summary="Get Ledger Entry",
    description="Fetch a specific ledger entry by ID.",
)
def get_ledger_entry(
    entry_id: int,
    service: LedgerService = Depends(get_ledger_service),
) -> LedgerEntryResponse:
    entry = service.get_entry(entry_id)
    return LedgerEntryResponse.model_validate(entry)


@router.get(
    "/reference/{reference_id}",
    response_model=List[LedgerEntryResponse],
    summary="Get Ledger Entries by Reference ID",
    description="Fetch the complete audit history for a reference transaction ID.",
)
def get_ledger_by_reference(
    reference_id: str,
    service: LedgerService = Depends(get_ledger_service),
) -> List[LedgerEntryResponse]:
    entries = service.get_by_reference_id(reference_id)
    return [LedgerEntryResponse.model_validate(e) for e in entries]
