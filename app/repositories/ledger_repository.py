from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.ledger_entry import LedgerEntry
from app.repositories.base import BaseRepository
from app.core.exceptions import BusinessRuleViolationException


class LedgerRepository(BaseRepository[LedgerEntry]):
    """
    Data access repository for LedgerEntry entities.
    Strictly enforces Append-Only semantics: updates and deletions are explicitly disallowed.
    """
    def __init__(self, db: Session):
        super().__init__(db, LedgerEntry)

    def update(self, entity: LedgerEntry) -> LedgerEntry:
        """Ledger entries are immutable. Updating is prohibited."""
        raise BusinessRuleViolationException("Ledger entries are strictly append-only. Updating is disallowed.")

    def delete(self, entity: LedgerEntry) -> None:
        """Ledger entries are immutable. Deletion is prohibited."""
        raise BusinessRuleViolationException("Ledger entries are strictly append-only. Deletion is disallowed.")

    def list_by_filters(
        self,
        customer_id: Optional[int] = None,
        invoice_id: Optional[int] = None,
        entry_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LedgerEntry]:
        """Query ledger entries filtered by domain criteria."""
        stmt = select(LedgerEntry)
        if customer_id is not None:
            stmt = stmt.where(LedgerEntry.customer_id == customer_id)
        if invoice_id is not None:
            stmt = stmt.where(LedgerEntry.invoice_id == invoice_id)
        if entry_type is not None:
            stmt = stmt.where(LedgerEntry.entry_type == entry_type)
        if reference_id is not None:
            stmt = stmt.where(LedgerEntry.reference_id == reference_id)

        stmt = stmt.order_by(LedgerEntry.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_by_reference_id(self, reference_id: str) -> List[LedgerEntry]:
        """Fetch all ledger audit events associated with a reference ID."""
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.reference_id == reference_id)
            .order_by(LedgerEntry.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
