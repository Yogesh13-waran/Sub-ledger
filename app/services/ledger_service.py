from decimal import Decimal
from typing import Optional, List
from app.models.ledger_entry import LedgerEntry
from app.repositories.ledger_repository import LedgerRepository
from app.core.exceptions import EntityNotFoundException


class LedgerService:
    """
    Business service for managing the append-only ledger audit trail.
    Enforces business rule: Ledger entries are append-only and traceable through reference_id.
    """
    def __init__(self, ledger_repo: LedgerRepository):
        self.ledger_repo = ledger_repo

    def record_entry(
        self,
        customer_id: Optional[int],
        invoice_id: Optional[int],
        entry_type: str,
        amount: Decimal,
        currency: str,
        reference_id: str,
        description: str,
    ) -> LedgerEntry:
        """
        Record an immutable event in the audit ledger.
        """
        entry = LedgerEntry(
            customer_id=customer_id,
            invoice_id=invoice_id,
            entry_type=entry_type,
            amount=amount,
            currency=currency.upper(),
            reference_id=str(reference_id),
            description=description,
        )
        return self.ledger_repo.create(entry)

    def get_entry(self, entry_id: int) -> LedgerEntry:
        """Fetch a specific ledger entry by ID."""
        entry = self.ledger_repo.get_by_id(entry_id)
        if not entry:
            raise EntityNotFoundException("LedgerEntry", entry_id)
        return entry

    def list_entries(
        self,
        customer_id: Optional[int] = None,
        invoice_id: Optional[int] = None,
        entry_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LedgerEntry]:
        """Query ledger entries filtered by domain criteria."""
        return self.ledger_repo.list_by_filters(
            customer_id=customer_id,
            invoice_id=invoice_id,
            entry_type=entry_type,
            reference_id=reference_id,
            skip=skip,
            limit=limit,
        )

    def get_by_reference_id(self, reference_id: str) -> List[LedgerEntry]:
        """Fetch audit log for a specific transaction reference."""
        return self.ledger_repo.list_by_reference_id(reference_id)
